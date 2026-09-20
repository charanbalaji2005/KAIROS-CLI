use anyhow::Result;
use crossterm::{
    event::{self, DisableMouseCapture, EnableMouseCapture, Event, KeyCode, KeyModifiers},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use ratatui::{
    backend::CrosstermBackend,
    layout::{Alignment, Constraint, Direction, Layout, Rect},
    style::{Modifier, Style},
    text::{Line, Span, Text},
    widgets::{Block, BorderType, Borders, List, ListItem, Paragraph, Wrap},
    Frame, Terminal,
};
use std::{io, sync::Arc, time::Duration};
use tokio::sync::{mpsc, Mutex};

use crate::{
    agent::{
        runtime::AgentRuntime,
        state::{AgentEvent, AgentState, ToolCall, ToolResult},
    },
    config::ForgeConfig,
    github::{GitDiffStat, GitHubClient, GitHubStatus},
    llm::provider::create_provider,
    ui::{mascot, theme::*, widgets::*},
};

// Slash commands
const SLASH_COMMANDS: &[(&str, &str)] = &[
    ("/help", "Show available commands"),
    ("/status", "Show agent and GitHub status"),
    ("/clear", "Clear conversation"),
    ("/compact", "Toggle compact mode"),
    ("/model", "Show/switch model"),
    ("/context", "Show context information"),
    ("/git", "Show git status"),
    ("/github", "Show GitHub status"),
    ("/diff", "Show current diff"),
    ("/plan", "Request a plan without executing"),
    ("/permissions", "Show permission settings"),
    ("/doctor", "Run environment check"),
    ("/exit", "Exit Forge"),
];

/// A rendered message in the conversation view
#[derive(Debug, Clone)]
pub enum DisplayMessage {
    UserInput(String),
    AgentText(String),
    ToolStart(String, String),   // name, input
    ToolDone(String, bool, String, u64), // name, success, output, ms
    ApprovalRequest(String, String), // command, description
    StatusLine(String),
    Separator,
    Error(String),
}

pub struct App {
    workspace: String,
    model: String,
    auto_mode: bool,
    config: ForgeConfig,

    // Input state
    input: String,
    cursor_pos: usize,
    history: Vec<String>,
    history_idx: Option<usize>,

    // Display
    messages: Vec<DisplayMessage>,
    scroll_offset: usize,

    // Agent state
    agent_state: AgentState,

    // GitHub / Git
    github_status: GitHubStatus,
    git_stat: GitDiffStat,

    // Slash command autocomplete
    showing_autocomplete: bool,
    autocomplete_items: Vec<String>,
    autocomplete_selected: usize,

    // Approval dialog
    showing_approval: Option<(String, String)>, // command, description

    // Animation tick
    tick: u64,

    // Compact mode
    compact_mode: bool,

    // Event channel
    event_rx: mpsc::UnboundedReceiver<AgentEvent>,
    event_tx: mpsc::UnboundedSender<AgentEvent>,

    // Runtime (shared with async tasks)
    runtime: Option<Arc<Mutex<AgentRuntime>>>,

    // State
    running: bool,
}

impl App {
    pub async fn new(
        workspace: String,
        model: String,
        auto_mode: bool,
        config: ForgeConfig,
    ) -> Result<Self> {
        let (event_tx, event_rx) = mpsc::unbounded_channel();

        // Detect GitHub status
        let github_status = GitHubClient::detect().await;
        let git_stat = GitHubClient::git_status().await.unwrap_or_default();

        Ok(Self {
            workspace,
            model,
            auto_mode,
            config,
            input: String::new(),
            cursor_pos: 0,
            history: Vec::new(),
            history_idx: None,
            messages: Vec::new(),
            scroll_offset: 0,
            agent_state: AgentState::Idle,
            github_status,
            git_stat,
            showing_autocomplete: false,
            autocomplete_items: Vec::new(),
            autocomplete_selected: 0,
            showing_approval: None,
            tick: 0,
            compact_mode: false,
            event_rx,
            event_tx,
            runtime: None,
            running: true,
        })
    }

    pub async fn run(&mut self) -> Result<()> {
        // Setup terminal
        enable_raw_mode()?;
        let mut stdout = io::stdout();
        execute!(stdout, EnterAlternateScreen)?;
        let backend = CrosstermBackend::new(stdout);
        let mut terminal = Terminal::new(backend)?;
        terminal.clear()?;

        // Initialize runtime
        self.init_runtime().await?;

        // Welcome message
        self.push_welcome();

        // Main event loop
        let tick_rate = Duration::from_millis(100);

        loop {
            terminal.draw(|f| self.render(f))?;

            // Poll for events
            if event::poll(tick_rate)? {
                if let Event::Key(key) = event::read()? {
                    self.handle_key(key).await?;
                }
            }

            // Process agent events
            self.drain_events();

            self.tick = self.tick.wrapping_add(1);

            if !self.running {
                break;
            }
        }

        // Cleanup
        disable_raw_mode()?;
        execute!(terminal.backend_mut(), LeaveAlternateScreen)?;
        terminal.show_cursor()?;

        Ok(())
    }

    async fn init_runtime(&mut self) -> Result<()> {
        let provider = create_provider(
            self.config.get_provider(),
            &self.model,
            &self.config,
        )
        .await?;

        let runtime = AgentRuntime::new(
            Arc::new(provider),
            self.workspace.clone(),
            self.auto_mode,
        );

        self.runtime = Some(Arc::new(Mutex::new(runtime)));
        Ok(())
    }

    fn push_welcome(&mut self) {
        self.messages.push(DisplayMessage::StatusLine(
            format!("Forge Agent v0.1.0 — Autonomous Terminal Engineer"),
        ));
        self.messages.push(DisplayMessage::StatusLine(
            format!("Model: {}  |  Workspace: {}", self.model, self.workspace),
        ));
        if self.github_status.connected {
            self.messages.push(DisplayMessage::StatusLine(format!(
                "GitHub: ● connected as {}",
                self.github_status.username.as_deref().unwrap_or("unknown")
            )));
        }
        self.messages.push(DisplayMessage::Separator);
        self.messages.push(DisplayMessage::StatusLine(
            "Type your task or /help for commands".to_string(),
        ));
    }

    fn drain_events(&mut self) {
        while let Ok(event) = self.event_rx.try_recv() {
            match event {
                AgentEvent::StateChanged(state) => {
                    self.agent_state = state;
                }
                AgentEvent::TextOutput(text) => {
                    self.messages.push(DisplayMessage::AgentText(text));
                }
                AgentEvent::ToolStarted(call) => {
                    self.messages.push(DisplayMessage::ToolStart(
                        call.name.clone(),
                        call.input.clone(),
                    ));
                }
                AgentEvent::ToolCompleted(result) => {
                    self.messages.push(DisplayMessage::ToolDone(
                        result.tool_name.clone(),
                        result.success,
                        result.output.clone(),
                        result.duration_ms,
                    ));
                }
                AgentEvent::ApprovalRequired { command, description } => {
                    self.showing_approval = Some((command, description));
                    self.agent_state = AgentState::WaitingApproval;
                }
                AgentEvent::Error(e) => {
                    self.messages.push(DisplayMessage::Error(e));
                    self.agent_state = AgentState::Failed("see above".to_string());
                }
                AgentEvent::Done => {
                    // Allow input again
                }
            }
        }
    }

    async fn handle_key(&mut self, key: crossterm::event::KeyEvent) -> Result<()> {
        use KeyCode::*;

        // Approval dialog takes priority
        if let Some((cmd, desc)) = &self.showing_approval.clone() {
            match key.code {
                Char('y') | Char('Y') => {
                    self.messages.push(DisplayMessage::StatusLine("✓ Approved".to_string()));
                    self.showing_approval = None;
                    self.agent_state = AgentState::Idle;
                }
                Char('n') | Char('N') | Esc => {
                    self.messages.push(DisplayMessage::StatusLine("✗ Denied".to_string()));
                    self.showing_approval = None;
                    self.agent_state = AgentState::Idle;
                }
                _ => {}
            }
            return Ok(());
        }

        // Autocomplete navigation
        if self.showing_autocomplete {
            match key.code {
                Up => {
                    if self.autocomplete_selected > 0 {
                        self.autocomplete_selected -= 1;
                    }
                    return Ok(());
                }
                Down => {
                    if self.autocomplete_selected + 1 < self.autocomplete_items.len() {
                        self.autocomplete_selected += 1;
                    }
                    return Ok(());
                }
                Tab | Enter => {
                    if let Some(item) = self.autocomplete_items.get(self.autocomplete_selected).cloned() {
                        self.input = item;
                        self.cursor_pos = self.input.len();
                        self.showing_autocomplete = false;
                    }
                    return Ok(());
                }
                Esc => {
                    self.showing_autocomplete = false;
                    return Ok(());
                }
                _ => {}
            }
        }

        match key.code {
            // Exit
            Char('c') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                self.running = false;
            }
            Char('d') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                self.running = false;
            }

            // Submit
            Enter => {
                self.submit_input().await?;
            }

            // Backspace
            Backspace => {
                if self.cursor_pos > 0 {
                    self.cursor_pos -= 1;
                    self.input.remove(self.cursor_pos);
                    self.update_autocomplete();
                }
            }

            Delete => {
                if self.cursor_pos < self.input.len() {
                    self.input.remove(self.cursor_pos);
                }
            }

            // Cursor movement
            Left => {
                if self.cursor_pos > 0 {
                    self.cursor_pos -= 1;
                }
            }
            Right => {
                if self.cursor_pos < self.input.len() {
                    self.cursor_pos += 1;
                }
            }
            Home => {
                self.cursor_pos = 0;
            }
            End => {
                self.cursor_pos = self.input.len();
            }

            // History
            Up => {
                self.history_up();
            }
            Down => {
                self.history_down();
            }

            // Page scroll
            PageUp => {
                if self.scroll_offset > 0 {
                    self.scroll_offset = self.scroll_offset.saturating_sub(5);
                }
            }
            PageDown => {
                self.scroll_offset += 5;
            }

            // Tab: autocomplete
            Tab => {
                if !self.showing_autocomplete && self.input.starts_with('/') {
                    self.update_autocomplete();
                    self.showing_autocomplete = !self.autocomplete_items.is_empty();
                }
            }

            // Character input
            Char(c) => {
                self.input.insert(self.cursor_pos, c);
                self.cursor_pos += 1;
                self.update_autocomplete();
            }

            Esc => {
                self.showing_autocomplete = false;
            }

            _ => {}
        }

        Ok(())
    }

    fn history_up(&mut self) {
        if self.history.is_empty() {
            return;
        }
        let new_idx = match self.history_idx {
            None => self.history.len() - 1,
            Some(0) => 0,
            Some(i) => i - 1,
        };
        self.history_idx = Some(new_idx);
        self.input = self.history[new_idx].clone();
        self.cursor_pos = self.input.len();
    }

    fn history_down(&mut self) {
        match self.history_idx {
            None => {}
            Some(i) if i + 1 >= self.history.len() => {
                self.history_idx = None;
                self.input.clear();
                self.cursor_pos = 0;
            }
            Some(i) => {
                let new_idx = i + 1;
                self.history_idx = Some(new_idx);
                self.input = self.history[new_idx].clone();
                self.cursor_pos = self.input.len();
            }
        }
    }

    fn update_autocomplete(&mut self) {
        if self.input.starts_with('/') {
            let prefix = self.input.to_lowercase();
            self.autocomplete_items = SLASH_COMMANDS
                .iter()
                .filter(|(cmd, _)| cmd.starts_with(&prefix))
                .map(|(cmd, _)| cmd.to_string())
                .collect();
            self.autocomplete_selected = 0;
            self.showing_autocomplete = !self.autocomplete_items.is_empty() && self.input.len() > 1;
        } else {
            self.showing_autocomplete = false;
        }
    }

    async fn submit_input(&mut self) -> Result<()> {
        let input = self.input.trim().to_string();
        if input.is_empty() {
            return Ok(());
        }

        // Save to history
        if self.history.last() != Some(&input) {
            self.history.push(input.clone());
        }
        self.history_idx = None;
        self.input.clear();
        self.cursor_pos = 0;
        self.showing_autocomplete = false;

        // Handle slash commands
        if input.starts_with('/') {
            self.handle_slash_command(&input).await?;
            return Ok(());
        }

        // Show user message
        self.messages.push(DisplayMessage::UserInput(input.clone()));
        self.messages.push(DisplayMessage::Separator);

        // Start agent processing in background
        if let Some(runtime) = &self.runtime {
            let runtime = Arc::clone(runtime);
            let event_tx = self.event_tx.clone();
            let input_clone = input.clone();

            tokio::spawn(async move {
                let mut rt = runtime.lock().await;
                if let Err(e) = rt.process(input_clone, event_tx.clone()).await {
                    let _ = event_tx.send(AgentEvent::Error(e.to_string()));
                }
            });
        } else {
            self.messages.push(DisplayMessage::Error(
                "Agent not initialized. Check model configuration.".to_string(),
            ));
        }

        Ok(())
    }

    async fn handle_slash_command(&mut self, cmd: &str) -> Result<()> {
        let parts: Vec<&str> = cmd.split_whitespace().collect();
        match parts.first().copied() {
            Some("/help") => {
                self.messages.push(DisplayMessage::StatusLine("FORGE COMMANDS".to_string()));
                for (cmd, desc) in SLASH_COMMANDS {
                    self.messages.push(DisplayMessage::StatusLine(
                        format!("  {:15}  {}", cmd, desc),
                    ));
                }
            }
            Some("/clear") => {
                self.messages.clear();
                self.push_welcome();
            }
            Some("/compact") => {
                self.compact_mode = !self.compact_mode;
                self.messages.push(DisplayMessage::StatusLine(
                    format!("Compact mode: {}", self.compact_mode),
                ));
            }
            Some("/model") => {
                self.messages.push(DisplayMessage::StatusLine(
                    format!("Current model: {}", self.model),
                ));
                self.messages.push(DisplayMessage::StatusLine(
                    "Available: qwen-coder, qwen-chat, qwen-think, deepseek-coder, claude-sonnet".to_string(),
                ));
            }
            Some("/git") => {
                let stat = GitHubClient::git_status().await.unwrap_or_default();
                let branch = self.github_status.branch.as_deref().unwrap_or("unknown");
                self.messages.push(DisplayMessage::StatusLine(format!(
                    "GIT  branch: {}  modified: {}  added: {}  deleted: {}  ahead: {}",
                    branch, stat.modified, stat.added, stat.deleted, stat.ahead
                )));
            }
            Some("/github") => {
                self.github_status = GitHubClient::detect().await;
                if self.github_status.connected {
                    self.messages.push(DisplayMessage::StatusLine(format!(
                        "GitHub ● connected  user: {}  repo: {}",
                        self.github_status.username.as_deref().unwrap_or("?"),
                        self.github_status.repo.as_deref().unwrap_or("?"),
                    )));
                } else {
                    self.messages.push(DisplayMessage::StatusLine(
                        "GitHub ○ not connected — run: gh auth login".to_string(),
                    ));
                }
            }
            Some("/diff") => {
                match crate::github::GitHubClient::diff_stat().await {
                    Ok(diff) => {
                        self.messages.push(DisplayMessage::StatusLine(
                            if diff.is_empty() { "No changes".to_string() } else { diff },
                        ));
                    }
                    Err(e) => {
                        self.messages.push(DisplayMessage::Error(e.to_string()));
                    }
                }
            }
            Some("/status") => {
                self.messages.push(DisplayMessage::StatusLine(
                    format!("Agent: {}  |  Model: {}", self.agent_state.label(), self.model),
                ));
            }
            Some("/exit") => {
                self.running = false;
            }
            Some("/doctor") => {
                // Quick checks inline
                let git_ok = std::process::Command::new("git")
                    .arg("--version").output().map(|o| o.status.success()).unwrap_or(false);
                let gh_ok = std::process::Command::new("gh")
                    .arg("--version").output().map(|o| o.status.success()).unwrap_or(false);
                let gh_auth = std::process::Command::new("gh")
                    .args(["auth", "status"]).output().map(|o| o.status.success()).unwrap_or(false);

                self.messages.push(DisplayMessage::StatusLine(
                    format!("{}  Git   {}  GitHub CLI   {}  GitHub Auth",
                        if git_ok { "✓" } else { "✗" },
                        if gh_ok { "✓" } else { "✗" },
                        if gh_auth { "✓" } else { "✗" },
                    )
                ));
            }
            Some("/permissions") => {
                self.messages.push(DisplayMessage::StatusLine(
                    format!("Auto mode: {}  (auto-approve all: {})", self.auto_mode, self.auto_mode),
                ));
                self.messages.push(DisplayMessage::StatusLine(
                    "Requires approval: git.push, github.pr.create, filesystem.delete".to_string(),
                ));
            }
            Some("/plan") => {
                self.messages.push(DisplayMessage::StatusLine(
                    "Plan-only mode: add your task after /plan".to_string(),
                ));
            }
            Some(other) => {
                self.messages.push(DisplayMessage::Error(
                    format!("Unknown command: {}. Try /help", other),
                ));
            }
            None => {}
        }
        Ok(())
    }

    // ─────────────────────────────────────────────────────
    // RENDER
    // ─────────────────────────────────────────────────────

    fn render(&self, frame: &mut Frame) {
        let area = frame.area();

        // Layout:
        //  header (4 lines)
        //  messages (fill)
        //  autocomplete (if showing, up to 10 lines)
        //  input (3 lines)
        //  footer (1 line)

        let header_h = if self.compact_mode { 2 } else { 4 };
        let footer_h = 1u16;
        let input_h = 3u16;
        let auto_h = if self.showing_autocomplete {
            (self.autocomplete_items.len().min(10) + 2) as u16
        } else {
            0
        };

        let msg_h = area
            .height
            .saturating_sub(header_h + footer_h + input_h + auto_h);

        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(header_h),
                Constraint::Length(msg_h),
                Constraint::Length(auto_h),
                Constraint::Length(input_h),
                Constraint::Length(footer_h),
            ])
            .split(area);

        self.render_header(frame, chunks[0]);
        self.render_messages(frame, chunks[1]);
        if self.showing_autocomplete {
            self.render_autocomplete(frame, chunks[2]);
        }
        self.render_input(frame, chunks[3]);
        self.render_footer(frame, chunks[4]);

        // Approval dialog overlay
        if let Some((cmd, desc)) = &self.showing_approval {
            self.render_approval_dialog(frame, area, cmd, desc);
        }
    }

    fn render_header(&self, frame: &mut Frame, area: Rect) {
        let branch = self.github_status.branch.as_deref().unwrap_or("main");
        let gh_user = self.github_status.username.as_deref().unwrap_or("—");
        let gh_connected = self.github_status.connected;
        let repo = self.github_status.repo.as_deref().unwrap_or("—");

        let block = Block::default()
            .style(Style::default().fg(TEXT_PRIMARY).bg(BG_SECONDARY));

        if self.compact_mode {
            // Single line compact header
            let line = Line::from(vec![
                Span::styled(" ⟦>_⟧ ", Style::default().fg(ORANGE_DARK)),
                Span::styled("FORGE", Style::default().fg(ORANGE).add_modifier(Modifier::BOLD)),
                Span::raw("  "),
                Span::styled(&self.model, Style::default().fg(TEXT_MUTED)),
                Span::raw("  "),
                Span::styled(&self.workspace, Style::default().fg(TEXT_DIM)),
                Span::raw("  "),
                if gh_connected {
                    Span::styled("GitHub ●", Style::default().fg(SUCCESS))
                } else {
                    Span::styled("GitHub ○", Style::default().fg(TEXT_DIM))
                },
            ]);
            let para = Paragraph::new(line).block(block);
            frame.render_widget(para, area);
        } else {
            // Full header with mascot
            let left_chunks = Layout::default()
                .direction(Direction::Horizontal)
                .constraints([Constraint::Length(8), Constraint::Min(0)])
                .split(area);

            // Mascot column
            let mascot_lines = mascot::mascot_lines();
            let mascot_para = Paragraph::new(mascot_lines)
                .style(Style::default().bg(BG_SECONDARY));
            frame.render_widget(mascot_para, left_chunks[0]);

            // Info column
            let gh_dot = if gh_connected { "●" } else { "○" };
            let gh_color = if gh_connected { SUCCESS } else { TEXT_DIM };
            let gh_text = if gh_connected {
                format!("{} {}", gh_dot, gh_user)
            } else {
                format!("{} disconnected", gh_dot)
            };

            let lines = vec![
                Line::from(vec![
                    Span::styled("FORGE AGENT", Style::default().fg(ORANGE).add_modifier(Modifier::BOLD)),
                    Span::styled(" v0.1.0", Style::default().fg(TEXT_MUTED)),
                    Span::raw("  "),
                    Span::styled("Autonomous Terminal Engineer", Style::default().fg(TEXT_DIM)),
                ]),
                Line::from(vec![
                    Span::styled("Model: ", Style::default().fg(TEXT_MUTED)),
                    Span::styled(&self.model, Style::default().fg(ORANGE_LIGHT)),
                    Span::styled("   Workspace: ", Style::default().fg(TEXT_MUTED)),
                    Span::styled(&self.workspace, Style::default().fg(TEXT_PRIMARY)),
                ]),
                Line::from(vec![
                    Span::styled("Branch: ", Style::default().fg(TEXT_MUTED)),
                    Span::styled(branch, Style::default().fg(ORANGE_FAINT)),
                    Span::styled("   GitHub: ", Style::default().fg(TEXT_MUTED)),
                    Span::styled(gh_text, Style::default().fg(gh_color)),
                    if gh_connected && !repo.is_empty() && repo != "—" {
                        Span::styled(format!("  {}", repo), Style::default().fg(TEXT_DIM))
                    } else {
                        Span::raw("")
                    },
                ]),
                Line::from(Span::styled(
                    "─".repeat(area.width as usize),
                    Style::default().fg(BORDER),
                )),
            ];

            let para = Paragraph::new(lines).block(block);
            frame.render_widget(para, left_chunks[1]);
        }
    }

    fn render_messages(&self, frame: &mut Frame, area: Rect) {
        let block = Block::default()
            .style(Style::default().bg(BG_PRIMARY));

        let width = area.width.saturating_sub(2) as usize;
        let mut lines: Vec<Line> = Vec::new();

        for msg in &self.messages {
            match msg {
                DisplayMessage::UserInput(text) => {
                    lines.push(Line::from(vec![
                        Span::styled("❯ ", Style::default().fg(ORANGE).add_modifier(Modifier::BOLD)),
                        Span::styled(text.clone(), Style::default().fg(TEXT_PRIMARY).add_modifier(Modifier::BOLD)),
                    ]));
                }

                DisplayMessage::AgentText(text) => {
                    lines.push(Line::from(vec![
                        Span::styled("Forge", Style::default().fg(ORANGE)),
                        Span::styled(":", Style::default().fg(BORDER)),
                    ]));
                    lines.push(Line::from(""));
                    // Word-wrap text
                    for para in text.split('\n') {
                        if para.is_empty() {
                            lines.push(Line::from(""));
                        } else {
                            let wrapped = textwrap::wrap(para, width.saturating_sub(2));
                            for w in wrapped {
                                lines.push(Line::from(vec![
                                    Span::raw("  "),
                                    Span::styled(w.to_string(), Style::default().fg(TEXT_PRIMARY)),
                                ]));
                            }
                        }
                    }
                    lines.push(Line::from(""));
                }

                DisplayMessage::ToolStart(name, input) => {
                    let sep = "─".repeat(width.saturating_sub(name.len() + 12));
                    lines.push(Line::from(vec![
                        Span::styled("┌─ ", Style::default().fg(BORDER)),
                        Span::styled(format!("tool: {}", name), Style::default().fg(ORANGE_LIGHT)),
                        Span::styled(format!(" {}", sep), Style::default().fg(BORDER)),
                        Span::styled("┐", Style::default().fg(BORDER)),
                    ]));
                    let display_input = if input.len() > width - 4 {
                        format!("{}…", &input[..width.saturating_sub(5)])
                    } else {
                        input.clone()
                    };
                    lines.push(Line::from(vec![
                        Span::styled("│ ", Style::default().fg(BORDER)),
                        Span::styled(display_input, Style::default().fg(TEXT_MUTED)),
                    ]));
                }

                DisplayMessage::ToolDone(name, success, output, ms) => {
                    let sep = "─".repeat(width.saturating_sub(4));
                    lines.push(Line::from(vec![
                        Span::styled("└", Style::default().fg(BORDER)),
                        Span::styled(sep, Style::default().fg(BORDER)),
                        Span::styled("┘", Style::default().fg(BORDER)),
                    ]));
                    if *success {
                        let short_output = if output.len() > 80 {
                            format!("{}…", &output[..77])
                        } else {
                            output.clone()
                        };
                        lines.push(Line::from(vec![
                            Span::styled("  ✓ ", Style::default().fg(SUCCESS)),
                            Span::styled(short_output, Style::default().fg(TEXT_MUTED)),
                            Span::styled(format!("  {}ms", ms), Style::default().fg(TEXT_DIM)),
                        ]));
                    } else {
                        lines.push(Line::from(vec![
                            Span::styled("  ✗ ", Style::default().fg(ERROR)),
                            Span::styled(output.clone(), Style::default().fg(ERROR)),
                        ]));
                    }
                    lines.push(Line::from(""));
                }

                DisplayMessage::ApprovalRequest(cmd, desc) => {
                    lines.push(Line::from(vec![
                        Span::styled("  ◆ APPROVAL REQUIRED: ", Style::default().fg(WARNING).add_modifier(Modifier::BOLD)),
                        Span::styled(cmd.clone(), Style::default().fg(TEXT_PRIMARY)),
                    ]));
                }

                DisplayMessage::StatusLine(text) => {
                    lines.push(Line::from(vec![
                        Span::styled("  ", Style::default()),
                        Span::styled(text.clone(), Style::default().fg(TEXT_MUTED)),
                    ]));
                }

                DisplayMessage::Separator => {
                    lines.push(Line::from(Span::styled(
                        "─".repeat(width),
                        Style::default().fg(BORDER),
                    )));
                }

                DisplayMessage::Error(e) => {
                    lines.push(Line::from(vec![
                        Span::styled("  ✗ ", Style::default().fg(ERROR)),
                        Span::styled(e.clone(), Style::default().fg(ERROR)),
                    ]));
                }
            }
        }

        // Agent thinking animation
        if matches!(
            self.agent_state,
            AgentState::Thinking | AgentState::Planning | AgentState::Reading | AgentState::Executing | AgentState::Testing
        ) {
            let spinner = ["◐", "◓", "◑", "◒"];
            let s = spinner[(self.tick / 3 % 4) as usize];
            lines.push(Line::from(vec![
                Span::styled(format!("  {} ", s), Style::default().fg(ORANGE)),
                Span::styled(self.agent_state.label(), Style::default().fg(TEXT_MUTED)),
            ]));
        }

        let total_lines = lines.len();
        let visible = area.height.saturating_sub(2) as usize;
        let scroll = if total_lines > visible {
            total_lines - visible
        } else {
            0
        };
        let scroll = scroll.saturating_sub(self.scroll_offset);

        let para = Paragraph::new(lines)
            .block(block)
            .scroll((scroll as u16, 0));

        frame.render_widget(para, area);
    }

    fn render_autocomplete(&self, frame: &mut Frame, area: Rect) {
        let items: Vec<ListItem> = self.autocomplete_items.iter().enumerate()
            .map(|(i, cmd)| {
                let desc = SLASH_COMMANDS.iter()
                    .find(|(c, _)| c == cmd)
                    .map(|(_, d)| *d)
                    .unwrap_or("");

                let style = if i == self.autocomplete_selected {
                    Style::default().fg(ORANGE).add_modifier(Modifier::BOLD)
                } else {
                    Style::default().fg(TEXT_MUTED)
                };

                ListItem::new(Line::from(vec![
                    Span::styled(format!("  {:15}", cmd), style),
                    Span::styled(desc, Style::default().fg(TEXT_DIM)),
                ]))
            })
            .collect();

        let list = List::new(items)
            .block(
                Block::default()
                    .borders(Borders::ALL)
                    .border_style(Style::default().fg(ORANGE_DARK))
                    .style(Style::default().bg(BG_ELEVATED)),
            );

        frame.render_widget(list, area);
    }

    fn render_input(&self, frame: &mut Frame, area: Rect) {
        let is_waiting = self.showing_approval.is_some();
        let is_busy = matches!(
            self.agent_state,
            AgentState::Thinking | AgentState::Planning | AgentState::Reading | AgentState::Executing | AgentState::Testing
        );

        let border_color = if is_waiting {
            WARNING
        } else if is_busy {
            ORANGE_DARK
        } else {
            BORDER
        };

        let block = Block::default()
            .borders(Borders::TOP)
            .border_style(Style::default().fg(border_color))
            .style(Style::default().bg(BG_SECONDARY));

        // Build input line with cursor
        let mut input_spans = vec![
            Span::styled("❯ ", Style::default().fg(ORANGE).add_modifier(Modifier::BOLD)),
        ];

        if is_waiting {
            input_spans.push(Span::styled(
                "[Y]es  [N]o  — Approve operation?",
                Style::default().fg(WARNING),
            ));
        } else {
            let before = &self.input[..self.cursor_pos];
            let cursor_char = self.input[self.cursor_pos..].chars().next().unwrap_or(' ');
            let after = if self.cursor_pos < self.input.len() {
                &self.input[self.cursor_pos + cursor_char.len_utf8()..]
            } else {
                ""
            };

            input_spans.push(Span::styled(before, Style::default().fg(TEXT_PRIMARY)));
            input_spans.push(Span::styled(
                cursor_char.to_string(),
                Style::default().fg(BG_PRIMARY).bg(ORANGE),
            ));
            if !after.is_empty() {
                input_spans.push(Span::styled(after, Style::default().fg(TEXT_PRIMARY)));
            }
        }

        let input_line = Line::from(input_spans);
        let para = Paragraph::new(Text::from(vec![
            Line::from(""),
            input_line,
        ]))
        .block(block);

        frame.render_widget(para, area);
    }

    fn render_footer(&self, frame: &mut Frame, area: Rect) {
        let mode_str = if self.auto_mode { "auto" } else { "manual" };
        let branch = self.github_status.branch.as_deref().unwrap_or("main");

        let git_info = format!("{}  {}", branch,
            if self.git_stat.modified > 0 || self.git_stat.added > 0 {
                format!("+{} ~{}", self.git_stat.added, self.git_stat.modified)
            } else {
                "clean".to_string()
            }
        );

        let state_sym = self.agent_state.symbol();
        let state_label = self.agent_state.label();

        let line = Line::from(vec![
            Span::styled(format!(" {} {} ", state_sym, mode_str),
                Style::default().fg(ORANGE).bg(BG_ELEVATED)),
            Span::styled("  ", Style::default().bg(BG_SECONDARY)),
            Span::styled(&self.model, Style::default().fg(TEXT_MUTED).bg(BG_SECONDARY)),
            Span::styled("  ", Style::default().bg(BG_SECONDARY)),
            if self.github_status.connected {
                Span::styled("GitHub ●", Style::default().fg(SUCCESS).bg(BG_SECONDARY))
            } else {
                Span::styled("GitHub ○", Style::default().fg(TEXT_DIM).bg(BG_SECONDARY))
            },
            Span::styled("  ", Style::default().bg(BG_SECONDARY)),
            Span::styled(git_info, Style::default().fg(TEXT_DIM).bg(BG_SECONDARY)),
            Span::styled("  ↑↓ history  Tab autocomplete  Ctrl+C exit",
                Style::default().fg(TEXT_DIM).bg(BG_SECONDARY)),
        ]);

        let para = Paragraph::new(line)
            .style(Style::default().bg(BG_SECONDARY));
        frame.render_widget(para, area);
    }

    fn render_approval_dialog(&self, frame: &mut Frame, area: Rect, cmd: &str, desc: &str) {
        let dialog_w = 60u16.min(area.width - 4);
        let dialog_h = 8u16;
        let x = (area.width - dialog_w) / 2;
        let y = (area.height - dialog_h) / 2;

        let dialog_area = Rect::new(x, y, dialog_w, dialog_h);

        // Clear background
        let bg = Block::default().style(Style::default().bg(BG_ELEVATED));
        frame.render_widget(bg, dialog_area);

        let lines = vec![
            Line::from(""),
            Line::from(vec![
                Span::styled("  Forge wants to execute:", Style::default().fg(TEXT_MUTED)),
            ]),
            Line::from(""),
            Line::from(vec![
                Span::styled(format!("  {}", cmd), Style::default().fg(ORANGE).add_modifier(Modifier::BOLD)),
            ]),
            Line::from(""),
            Line::from(vec![
                Span::styled(format!("  {}", desc), Style::default().fg(TEXT_DIM)),
            ]),
            Line::from(""),
            Line::from(vec![
                Span::styled("  [Y] Allow    ", Style::default().fg(SUCCESS)),
                Span::styled("[N] Deny", Style::default().fg(ERROR)),
            ]),
        ];

        let dialog = Paragraph::new(lines)
            .block(
                Block::default()
                    .title(" ◆ APPROVAL REQUIRED ")
                    .title_style(Style::default().fg(WARNING).add_modifier(Modifier::BOLD))
                    .borders(Borders::ALL)
                    .border_style(Style::default().fg(WARNING))
                    .style(Style::default().bg(BG_ELEVATED)),
            );

        frame.render_widget(dialog, dialog_area);
    }
}

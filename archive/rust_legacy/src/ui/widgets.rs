use ratatui::{
    style::{Modifier, Style},
    text::{Line, Span},
    widgets::{Block, BorderType, Borders},
};
use crate::ui::theme::*;

/// Forge-branded block with orange top border
pub fn forge_block(title: &str) -> Block<'_> {
    Block::default()
        .title(format!(" {} ", title))
        .title_style(Style::default().fg(ORANGE).add_modifier(Modifier::BOLD))
        .borders(Borders::ALL)
        .border_type(BorderType::Plain)
        .border_style(style_border())
        .style(style_default())
}

/// Active block with highlighted border
pub fn forge_block_active(title: &str) -> Block<'_> {
    Block::default()
        .title(format!(" {} ", title))
        .title_style(Style::default().fg(ORANGE).add_modifier(Modifier::BOLD))
        .borders(Borders::ALL)
        .border_type(BorderType::Plain)
        .border_style(style_border_active())
        .style(style_default())
}

/// Tool execution block
pub fn tool_block(tool_name: &str) -> Vec<Line<'static>> {
    let separator = "─".repeat(50);
    let name = tool_name.to_string();
    let sep = separator.clone();
    vec![
        Line::from(vec![
            Span::styled("┌─ ", Style::default().fg(BORDER)),
            Span::styled(format!("tool: {}", name), Style::default().fg(ORANGE)),
            Span::styled(format!(" {}", sep), Style::default().fg(BORDER)),
        ]),
    ]
}

/// Render a status line: symbol + label in appropriate color
pub fn status_line<'a>(
    state: &'a crate::agent::state::AgentState,
) -> Line<'a> {
    Line::from(vec![
        Span::styled(
            state.symbol(),
            Style::default().fg(state_color(state)),
        ),
        Span::raw(" "),
        Span::styled(
            state.label(),
            Style::default().fg(TEXT_MUTED),
        ),
    ])
}

/// A separator line
pub fn separator_line(width: usize) -> Line<'static> {
    Line::from(Span::styled(
        "─".repeat(width),
        Style::default().fg(BORDER),
    ))
}

/// A prompt line for user input
pub fn prompt_line() -> Span<'static> {
    Span::styled("❯ ", Style::default().fg(ORANGE).add_modifier(Modifier::BOLD))
}

/// Format a success message
pub fn success_span(text: &str) -> Span {
    Span::styled(
        format!("✓ {}", text),
        Style::default().fg(SUCCESS),
    )
}

/// Format an error message
pub fn error_span(text: &str) -> Span {
    Span::styled(
        format!("✗ {}", text),
        Style::default().fg(ERROR),
    )
}

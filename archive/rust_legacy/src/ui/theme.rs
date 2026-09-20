use ratatui::style::{Color, Modifier, Style};

// Forge Brand Colors
pub const ORANGE: Color = Color::Rgb(249, 115, 22);
pub const ORANGE_DARK: Color = Color::Rgb(234, 88, 12);
pub const ORANGE_LIGHT: Color = Color::Rgb(251, 146, 60);
pub const ORANGE_FAINT: Color = Color::Rgb(253, 186, 116);

// Backgrounds
pub const BG_PRIMARY: Color = Color::Rgb(17, 17, 17);
pub const BG_SECONDARY: Color = Color::Rgb(23, 23, 23);
pub const BG_SURFACE: Color = Color::Rgb(28, 28, 28);
pub const BG_ELEVATED: Color = Color::Rgb(34, 34, 34);

// Text
pub const TEXT_PRIMARY: Color = Color::Rgb(245, 245, 245);
pub const TEXT_MUTED: Color = Color::Rgb(163, 163, 163);
pub const TEXT_DIM: Color = Color::Rgb(82, 82, 82);

// Borders
pub const BORDER: Color = Color::Rgb(58, 58, 58);
pub const BORDER_ACTIVE: Color = ORANGE_DARK;

// Status
pub const SUCCESS: Color = Color::Rgb(34, 197, 94);
pub const WARNING: Color = Color::Rgb(245, 158, 11);
pub const ERROR: Color = Color::Rgb(239, 68, 68);
pub const INFO: Color = Color::Rgb(99, 179, 237);

// Styles
pub fn style_default() -> Style {
    Style::default().fg(TEXT_PRIMARY).bg(BG_PRIMARY)
}

pub fn style_orange() -> Style {
    Style::default().fg(ORANGE)
}

pub fn style_orange_bold() -> Style {
    Style::default().fg(ORANGE).add_modifier(Modifier::BOLD)
}

pub fn style_muted() -> Style {
    Style::default().fg(TEXT_MUTED)
}

pub fn style_dim() -> Style {
    Style::default().fg(TEXT_DIM)
}

pub fn style_success() -> Style {
    Style::default().fg(SUCCESS)
}

pub fn style_error() -> Style {
    Style::default().fg(ERROR)
}

pub fn style_warning() -> Style {
    Style::default().fg(WARNING)
}

pub fn style_header() -> Style {
    Style::default().fg(TEXT_PRIMARY).bg(BG_SECONDARY)
}

pub fn style_selected() -> Style {
    Style::default().fg(ORANGE).bg(BG_ELEVATED).add_modifier(Modifier::BOLD)
}

pub fn style_input() -> Style {
    Style::default().fg(TEXT_PRIMARY).bg(BG_SECONDARY)
}

pub fn style_tool_block() -> Style {
    Style::default().fg(TEXT_MUTED).bg(BG_SURFACE)
}

pub fn style_border() -> Style {
    Style::default().fg(BORDER)
}

pub fn style_border_active() -> Style {
    Style::default().fg(ORANGE_DARK)
}

// State colors
pub fn state_color(state: &crate::agent::state::AgentState) -> Color {
    use crate::agent::state::AgentState;
    match state {
        AgentState::Idle => SUCCESS,
        AgentState::Thinking => ORANGE,
        AgentState::Planning => ORANGE_LIGHT,
        AgentState::Reading => INFO,
        AgentState::Executing => WARNING,
        AgentState::Testing => ORANGE,
        AgentState::WaitingApproval => WARNING,
        AgentState::Completed => SUCCESS,
        AgentState::Failed(_) => ERROR,
    }
}

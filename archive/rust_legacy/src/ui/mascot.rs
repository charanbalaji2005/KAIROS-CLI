use ratatui::{
    layout::Rect,
    style::{Color, Style},
    text::{Line, Span},
    widgets::{Block, Paragraph},
    Frame,
};
use crate::ui::theme::*;

/// The Forge mascot as colored Unicode art (fits in ~9x7 cells)
pub fn mascot_lines() -> Vec<Line<'static>> {
    vec![
        Line::from(vec![
            Span::styled("  ╭──╮  ", Style::default().fg(ORANGE_DARK)),
        ]),
        Line::from(vec![
            Span::styled("╭┤", Style::default().fg(ORANGE_DARK)),
            Span::styled(">_", Style::default().fg(ORANGE_FAINT)),
            Span::styled("├╮", Style::default().fg(ORANGE_DARK)),
        ]),
        Line::from(vec![
            Span::styled("╰┤", Style::default().fg(ORANGE_DARK)),
            Span::styled("██", Style::default().fg(ORANGE)),
            Span::styled("├╯", Style::default().fg(ORANGE_DARK)),
        ]),
        Line::from(vec![
            Span::styled(" ╰────╯ ", Style::default().fg(ORANGE_DARK)),
        ]),
    ]
}

/// Render mascot inline in a small rect
pub fn render_mascot_inline(frame: &mut Frame, area: Rect) {
    let lines = mascot_lines();
    let para = Paragraph::new(lines);
    frame.render_widget(para, area);
}

/// The pixel mascot in a slightly larger format for startup screen
pub fn startup_mascot() -> Vec<String> {
    vec![
        "    ╔══╗    ".to_string(),
        "  ╔═╣  ╠═╗  ".to_string(),
        " ╔╣ ╠══╣ ╠╗ ".to_string(),
        " ║║ >_   ║║ ".to_string(),
        " ╚╣ ╠══╣ ╠╝ ".to_string(),
        "  ╚═╣██╠═╝  ".to_string(),
        "   ╔╝  ╚╗   ".to_string(),
        "   ╚════╝   ".to_string(),
    ]
}

/// Simple inline mascot for the header (compact)
pub fn header_mascot_spans() -> Vec<Span<'static>> {
    vec![
        Span::styled("⟦", Style::default().fg(ORANGE_DARK)),
        Span::styled(">_", Style::default().fg(ORANGE_FAINT)),
        Span::styled("⟧", Style::default().fg(ORANGE_DARK)),
    ]
}

/// Status dot
pub fn status_dot(connected: bool) -> Span<'static> {
    if connected {
        Span::styled("●", Style::default().fg(Color::Rgb(34, 197, 94)))
    } else {
        Span::styled("○", Style::default().fg(Color::Rgb(163, 163, 163)))
    }
}

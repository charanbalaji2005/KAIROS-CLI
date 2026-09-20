/// Planner module — generates structured plans before execution
pub struct Planner;

impl Planner {
    pub fn new() -> Self {
        Self
    }

    /// Format a numbered plan from text
    pub fn format_plan(steps: &[&str]) -> String {
        steps
            .iter()
            .enumerate()
            .map(|(i, step)| format!("{:02}  {}", i + 1, step))
            .collect::<Vec<_>>()
            .join("\n")
    }
}

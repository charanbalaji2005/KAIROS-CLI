mod cli;
mod ui;
mod agent;
mod tools;
mod github;
mod llm;
mod memory;
mod security;
mod config;

use anyhow::Result;
use clap::{Parser, Subcommand};
use tracing_subscriber::{fmt, prelude::*, EnvFilter};

#[derive(Parser)]
#[command(
    name = "forge",
    version = "0.1.0",
    about = "FORGE - Autonomous Terminal Engineer",
    long_about = "Forge is an AI-powered terminal coding agent capable of understanding repositories,\nediting code, running tests, and pushing to GitHub autonomously."
)]
struct Cli {
    #[command(subcommand)]
    command: Option<Commands>,

    /// Path to workspace directory
    #[arg(short, long, global = true)]
    workspace: Option<String>,

    /// Model to use (e.g., qwen-coder, qwen-chat, qwen-think)
    #[arg(short, long, global = true)]
    model: Option<String>,

    /// Enable verbose output
    #[arg(short, long, global = true)]
    verbose: bool,

    /// Run without confirmation prompts (auto mode)
    #[arg(short, long, global = true)]
    auto: bool,
}

#[derive(Subcommand)]
enum Commands {
    /// Run Forge doctor to check environment
    Doctor,
    /// List available models
    #[command(name = "model")]
    Model {
        #[command(subcommand)]
        action: ModelAction,
    },
    /// Show version and update status
    Version,
    /// Show current status
    Status,
    /// Update Forge to latest version
    Update,
    /// Configure Forge settings
    Config {
        #[arg(value_name = "KEY")]
        key: Option<String>,
        #[arg(value_name = "VALUE")]
        value: Option<String>,
    },
    /// Start interactive session (default)
    Start,
}

#[derive(Subcommand)]
enum ModelAction {
    /// List available models
    List,
    /// Show current model status
    Status,
    /// Set active model
    Set { model: String },
    /// Install a local model
    Install { model: String },
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging (only in verbose mode)
    let filter = EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("warn"));
    tracing_subscriber::registry()
        .with(fmt::layer().with_target(false))
        .with(filter)
        .init();

    let cli_args = Cli::parse();

    // Load config
    let cfg = config::ForgeConfig::load().await?;

    match cli_args.command {
        Some(Commands::Doctor) => {
            cli::commands::run_doctor().await?;
        }
        Some(Commands::Model { action }) => {
            cli::commands::run_model(action, &cfg).await?;
        }
        Some(Commands::Version) => {
            cli::commands::run_version().await?;
        }
        Some(Commands::Status) => {
            cli::commands::run_status(&cfg).await?;
        }
        Some(Commands::Update) => {
            cli::commands::run_update().await?;
        }
        Some(Commands::Config { key, value }) => {
            cli::commands::run_config(key, value, &cfg).await?;
        }
        Some(Commands::Start) | None => {
            // Launch interactive TUI
            let workspace = cli_args.workspace
                .unwrap_or_else(|| std::env::current_dir()
                    .unwrap_or_default()
                    .to_string_lossy()
                    .to_string());

            let model = cli_args.model
                .unwrap_or_else(|| cfg.model.clone().unwrap_or_else(|| "qwen-coder".to_string()));

            let mut app = ui::App::new(workspace, model, cli_args.auto, cfg).await?;
            app.run().await?;
        }
    }

    Ok(())
}

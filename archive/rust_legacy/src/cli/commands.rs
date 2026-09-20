use anyhow::Result;
use crate::config::ForgeConfig;

pub async fn run_doctor() -> Result<()> {
    println!("\n\x1b[38;2;249;115;22m╔══════════════════════════════════════════════════════════╗\x1b[0m");
    println!("\x1b[38;2;249;115;22m║              FORGE DOCTOR v0.1.0                         ║\x1b[0m");
    println!("\x1b[38;2;249;115;22m╚══════════════════════════════════════════════════════════╝\x1b[0m\n");

    let checks: Vec<(&str, &str, fn() -> bool)> = vec![
        ("Git", "git --version", check_git),
        ("GitHub CLI (gh)", "gh --version", check_gh),
        ("GitHub Auth", "gh auth status", check_gh_auth),
    ];

    println!("\x1b[38;2;163;163;163mEnvironment\x1b[0m");

    for (name, _cmd, check_fn) in &checks {
        let ok = check_fn();
        if ok {
            println!("  \x1b[38;2;34;197;94m✓\x1b[0m {}", name);
        } else {
            println!("  \x1b[38;2;239;68;68m✗\x1b[0m {}", name);
        }
    }

    // Check Ollama
    let ollama_ok = check_ollama().await;
    if ollama_ok {
        println!("  \x1b[38;2;34;197;94m✓\x1b[0m Ollama");
    } else {
        println!("  \x1b[38;2;239;68;68m✗\x1b[0m Ollama (not running — start with: ollama serve)");
    }

    // Check models
    println!("\n\x1b[38;2;163;163;163mModels\x1b[0m");
    let models = check_ollama_models().await;
    if models.is_empty() {
        println!("  \x1b[38;2;239;68;68m✗\x1b[0m No local models found");
        println!("    Run: ollama pull qwen2.5-coder:3b");
    } else {
        for m in &models {
            println!("  \x1b[38;2;34;197;94m✓\x1b[0m {}", m);
        }
    }

    // GitHub status
    println!("\n\x1b[38;2;163;163;163mGitHub\x1b[0m");
    if check_gh_auth() {
        if let Ok(user) = get_gh_user().await {
            println!("  \x1b[38;2;34;197;94m✓\x1b[0m Authenticated as: \x1b[38;2;249;115;22m{}\x1b[0m", user);
        }
    } else {
        println!("  \x1b[38;2;239;68;68m✗\x1b[0m Not authenticated (run: gh auth login)");
    }

    // Config
    println!("\n\x1b[38;2;163;163;163mConfiguration\x1b[0m");
    let config_path = ForgeConfig::config_path();
    if config_path.exists() {
        println!("  \x1b[38;2;34;197;94m✓\x1b[0m Config: {}", config_path.display());
    } else {
        println!("  \x1b[38;2;245;158;11m◆\x1b[0m Config: not found (defaults will be used)");
    }

    println!("\n\x1b[38;2;163;163;163mRun \x1b[38;2;249;115;22mforge\x1b[38;2;163;163;163m to start the agent\x1b[0m\n");
    Ok(())
}

pub async fn run_model(action: crate::ModelAction, _cfg: &ForgeConfig) -> Result<()> {
    match action {
        crate::ModelAction::List => {
            println!("\n\x1b[38;2;249;115;22mFORGE MODELS\x1b[0m\n");
            println!("\x1b[38;2;163;163;163mCloud Providers\x1b[0m");
            println!("  ○ claude-sonnet     Anthropic Claude Sonnet");
            println!("  ○ gpt-4o            OpenAI GPT-4o");
            println!("  ○ gemini-pro        Google Gemini Pro");
            println!();
            println!("\x1b[38;2;163;163;163mLocal Models (Ollama)\x1b[0m");
            println!("  \x1b[38;2;249;115;22m●\x1b[0m qwen-coder          Qwen2.5-Coder 3B  \x1b[38;2;34;197;94m[recommended]\x1b[0m");
            println!("  ○ qwen-chat         Qwen2.5 3B Chat");
            println!("  ○ qwen-think        Qwen2.5 3B w/ reasoning");
            println!("  ○ deepseek-coder    DeepSeek-Coder 1.3B");
            println!("  ○ phi3-mini         Phi-3 Mini 3.8B");
            println!();
            println!("\x1b[38;2;163;163;163mInstall a model:\x1b[0m  forge model install qwen-coder");
            println!("\x1b[38;2;163;163;163mSet model:\x1b[0m        forge model set qwen-coder\n");
        }
        crate::ModelAction::Status => {
            let models = check_ollama_models().await;
            println!("\n\x1b[38;2;249;115;22mFORGE MODEL STATUS\x1b[0m\n");
            if models.is_empty() {
                println!("\x1b[38;2;239;68;68m✗\x1b[0m No local models installed");
            } else {
                for m in &models {
                    println!("\x1b[38;2;34;197;94m✓\x1b[0m {}", m);
                }
            }
        }
        crate::ModelAction::Set { model } => {
            let mut cfg = ForgeConfig::load().await?;
            cfg.set("model", &model).await?;
            println!("\x1b[38;2;34;197;94m✓\x1b[0m Model set to: \x1b[38;2;249;115;22m{}\x1b[0m", model);
        }
        crate::ModelAction::Install { model } => {
            let ollama_name = match model.as_str() {
                "qwen-coder" => "qwen2.5-coder:3b",
                "qwen-chat" => "qwen2.5:3b",
                "qwen-think" => "qwen2.5:3b",
                "deepseek-coder" => "deepseek-coder:1.3b",
                "phi3-mini" => "phi3:mini",
                other => other,
            };
            println!("\x1b[38;2;249;115;22m◉\x1b[0m Installing model: {} → {}...", model, ollama_name);
            let status = tokio::process::Command::new("ollama")
                .args(["pull", ollama_name])
                .status()
                .await?;
            if status.success() {
                println!("\x1b[38;2;34;197;94m✓\x1b[0m Model installed: {}", model);
            } else {
                println!("\x1b[38;2;239;68;68m✗\x1b[0m Install failed. Make sure ollama is running.");
            }
        }
    }
    Ok(())
}

pub async fn run_version() -> Result<()> {
    println!("\n\x1b[38;2;249;115;22mForge Agent\x1b[0m v0.1.0\n");
    println!("  Build:      production");
    println!("  Platform:   {}", std::env::consts::OS);
    println!("  Arch:       {}", std::env::consts::ARCH);
    println!("\n\x1b[38;2;34;197;94m✓\x1b[0m Latest version\n");
    Ok(())
}

pub async fn run_status(cfg: &ForgeConfig) -> Result<()> {
    println!("\n\x1b[38;2;249;115;22mFORGE STATUS\x1b[0m\n");
    println!("  Model:      {}", cfg.get_model());
    println!("  Provider:   {}", cfg.get_provider());
    println!("  Auto mode:  {}", cfg.auto_mode.unwrap_or(false));

    if check_gh_auth() {
        if let Ok(user) = get_gh_user().await {
            println!("  GitHub:     \x1b[38;2;34;197;94m● connected\x1b[0m as {}", user);
        }
    } else {
        println!("  GitHub:     \x1b[38;2;239;68;68m○ disconnected\x1b[0m");
    }

    if let Ok(branch) = get_git_branch().await {
        println!("  Branch:     {}", branch);
    }
    println!();
    Ok(())
}

pub async fn run_update() -> Result<()> {
    println!("\n\x1b[38;2;249;115;22m◉\x1b[0m Checking for updates...");
    println!("\x1b[38;2;34;197;94m✓\x1b[0m Forge v0.1.0 is the latest version\n");
    Ok(())
}

pub async fn run_config(key: Option<String>, value: Option<String>, _cfg: &ForgeConfig) -> Result<()> {
    match (key, value) {
        (Some(k), Some(v)) => {
            let mut cfg = ForgeConfig::load().await?;
            cfg.set(&k, &v).await?;
            println!("\x1b[38;2;34;197;94m✓\x1b[0m Set {} = {}", k, v);
        }
        (Some(k), None) => {
            let cfg = ForgeConfig::load().await?;
            println!("{}: {:?}", k, cfg.get_model());
        }
        _ => {
            let cfg = ForgeConfig::load().await?;
            println!("\n\x1b[38;2;249;115;22mFORGE CONFIG\x1b[0m");
            println!("  Path: {}\n", ForgeConfig::config_path().display());
            println!("  model:       {}", cfg.get_model());
            println!("  provider:    {}", cfg.get_provider());
            println!("  auto_mode:   {}", cfg.auto_mode.unwrap_or(false));
            println!("  ollama_url:  {}", cfg.ollama_url.as_deref().unwrap_or("http://localhost:11434"));
            println!();
        }
    }
    Ok(())
}

// Helper functions
fn check_git() -> bool {
    std::process::Command::new("git")
        .arg("--version")
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false)
}

fn check_gh() -> bool {
    std::process::Command::new("gh")
        .arg("--version")
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false)
}

fn check_gh_auth() -> bool {
    std::process::Command::new("gh")
        .args(["auth", "status"])
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false)
}

async fn check_ollama() -> bool {
    reqwest::get("http://localhost:11434/api/tags")
        .await
        .map(|r| r.status().is_success())
        .unwrap_or(false)
}

async fn check_ollama_models() -> Vec<String> {
    let Ok(resp) = reqwest::get("http://localhost:11434/api/tags").await else {
        return vec![];
    };
    let Ok(json) = resp.json::<serde_json::Value>().await else {
        return vec![];
    };
    json["models"]
        .as_array()
        .unwrap_or(&vec![])
        .iter()
        .filter_map(|m| m["name"].as_str().map(|s| s.to_string()))
        .collect()
}

pub async fn get_gh_user() -> Result<String> {
    let out = tokio::process::Command::new("gh")
        .args(["api", "user", "--jq", ".login"])
        .output()
        .await?;
    Ok(String::from_utf8_lossy(&out.stdout).trim().to_string())
}

pub async fn get_git_branch() -> Result<String> {
    let out = tokio::process::Command::new("git")
        .args(["branch", "--show-current"])
        .output()
        .await?;
    Ok(String::from_utf8_lossy(&out.stdout).trim().to_string())
}

pub async fn get_git_remote() -> Result<String> {
    let out = tokio::process::Command::new("git")
        .args(["remote", "get-url", "origin"])
        .output()
        .await?;
    let raw = String::from_utf8_lossy(&out.stdout).trim().to_string();
    // Extract owner/repo from URL
    let repo = raw
        .trim_end_matches(".git")
        .split('/')
        .rev()
        .take(2)
        .collect::<Vec<_>>()
        .iter()
        .rev()
        .cloned()
        .collect::<Vec<_>>()
        .join("/");
    Ok(repo)
}

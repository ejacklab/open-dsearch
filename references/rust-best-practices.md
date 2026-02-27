# Rust Development Best Practices

## Cargo.toml Setup

### TLS Backend (Avoid OpenSSL)

Always specify `rustls-tls` to avoid OpenSSL dependency issues:

```toml
[dependencies]
reqwest = { version = "0.12", default-features = false, features = ["rustls-tls", "blocking"] }
```

### Disable Default Features

Only include features you need to reduce binary size and compile time:

```toml
# Bad - pulls in all default features
reqwest = "0.12"

# Good - explicit features only
reqwest = { version = "0.12", default-features = false, features = ["blocking", "rustls-tls"] }
```

## Build Preventative Measures

### 1. Gitignore Setup

Create `.gitignore` before first commit:

```
target/
*.exe
*.dSYM
Cargo.lock  # Only for libraries, not binaries
```

### 2. Always Commit Cargo.lock

For reproducible builds:

```bash
git add Cargo.lock
```

### 3. Check Crate Versions First

```bash
cargo search <crate> | head -5
```

Or check crates.io directly to verify version exists.

## Error Handling Pattern

```rust
fn run() -> Result<(), String> {
    // Main logic
    let client = Client::builder()
        .build()
        .map_err(|e| e.to_string())?;
    
    Ok(())
}

fn main() {
    if let Err(e) = run() {
        eprintln!("Error: {}", e);
        std::process::exit(1);
    }
}
```

## Binary Size Optimization

### 1. Strip Symbols

```bash
cargo build --release --strip
```

### 2. LTO (Link Time Optimization)

```toml
[profile.release]
lto = true
codegen-units = 1
```

### 3. Use staticlib for system crates

```toml
[dependencies]
staticlib = "1.0"
```

## Cross-Platform Builds

### Add Target Platforms

```bash
rustup target add x86_64-pc-windows-gnu
```

### Build for Target

```bash
cargo build --target x86_64-pc-windows-gnu
```

## Dependency Auditing

### Check for Vulnerabilities

```bash
cargo audit
```

### Check for Duplicates

```bash
cargo tree -d
```

### Check for Unused Dependencies

```bash
cargo machete
```

## Common Crate Recommendations

| Purpose | Recommended Crate |
|---------|-----------------|
| HTTP Client | reqwest (with rustls-tls) |
| HTML Parsing | scraper |
| HTML to Markdown | html2md |
| CLI Args | clap (derive macros) |
| Async Runtime | tokio |
| Serialization | serde + serde_json |
| Logging | log facade + tracing |
| URL Parsing | url |

## Performance Tips

### 1. Use Blocking vs Async

For simple CLI tools, blocking is easier:

```rust
use reqwest::blocking::Client;
```

### 2. Reuse HTTP Client

Create client once, reuse for all requests:

```rust
let client = Client::new();
// Use client for multiple requests
```

### 3. Limit Response Size

```rust
let response = client.get(&url)
    .timeout(Duration::from_secs(30))
    .send()?;
```

## Debugging Build Issues

### Missing TLS

```
error: failed to run custom build command for `openssl-sys`
```

**Solution**: Use `rustls-tls` feature instead of default.

### Missing pkg-config

```
Could not find pkg-config
```

**Solution**: Install `pkg-config` or use rustls-tls.

### Compilation Timeout

```
warning: build timed out
```

**Solution**: Use `--jobs 1` or reduce parallelism.

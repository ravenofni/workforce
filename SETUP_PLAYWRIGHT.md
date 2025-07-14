# Playwright Setup Guide for Workforce Analytics

This guide provides detailed instructions for setting up Playwright for PDF generation in the Workforce Analytics System.

## Why Playwright?

Playwright is the modern replacement for pyppeteer with several advantages:
- **Actively maintained** by Microsoft (pyppeteer is deprecated)
- **Better performance** and stability
- **Cross-browser support** (Chromium, Firefox, WebKit)
- **Enhanced debugging** and development tools
- **Built-in waiting strategies** for reliable PDF generation

## Installation Steps

### 1. Install Playwright Python Package

```bash
pip install playwright
```

### 2. Install Browser Binaries

Playwright requires browser binaries to be installed separately:

```bash
# Install only Chromium (recommended for PDF generation)
playwright install chromium

# Or install all browsers (optional)
playwright install
```

### 3. Verify Installation

```bash
# Test Playwright installation
python -c "from playwright.sync_api import sync_playwright; print('✅ Playwright successfully installed')"
```

## System Requirements

### Disk Space
- **Chromium**: ~150MB
- **All browsers**: ~1GB

### Memory
- **Minimum**: 2GB RAM
- **Recommended**: 4GB+ RAM for large datasets

### Operating Systems
- **Linux**: Ubuntu 18.04+, CentOS 8+, Debian 10+
- **macOS**: 10.15+ (Catalina)
- **Windows**: Windows 10+

## Docker Deployment

For containerized deployments:

```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# Browsers are pre-installed in the official image
COPY . .
CMD ["python", "main.py", "--help"]
```

## Troubleshooting

### Common Issues

**1. Browser Not Found**
```bash
Error: Executable doesn't exist at /home/user/.cache/ms-playwright/chromium-*/chrome-linux/chrome
```
**Solution**: Run `playwright install chromium`

**2. Permission Denied (Linux)**
```bash
Error: Permission denied: '/home/user/.cache/ms-playwright'
```
**Solution**: 
```bash
sudo chown -R $USER:$USER ~/.cache/ms-playwright
# Or install system-wide:
sudo playwright install chromium
```

**3. Dependencies Missing (Linux)**
```bash
Error: Host system is missing dependencies to run browsers
```
**Solution**:
```bash
# Ubuntu/Debian
sudo playwright install-deps chromium

# Or manually install:
sudo apt-get update
sudo apt-get install -y libnss3 libxss1 libasound2
```

### Debugging PDF Generation

Enable debug logging for Playwright:

```bash
# Set environment variable for detailed logs
export DEBUG=pw:api
python main.py --facility-data data.csv --model-data model.csv --log-level DEBUG
```

### Performance Optimization

For production environments:

```python
# In config/constants.py, you can adjust PDF settings:
PDF_TIMEOUT = 30000  # 30 seconds (default: 60 seconds)
PDF_MARGIN_INCHES = 0.5  # Smaller margins for more content
```

## Migration from pyppeteer

The system automatically detects and uses Playwright instead of pyppeteer. Key changes:

1. **Browser Launch**: Uses `playwright.chromium.launch()` instead of `pyppeteer.launch()`
2. **PDF Generation**: Uses Playwright's `page.pdf()` method with updated parameter names
3. **Context Management**: Uses Playwright's context management for better resource handling
4. **Waiting Strategies**: Uses `wait_until='networkidle'` for more reliable rendering

## CI/CD Integration

### GitHub Actions

```yaml
- name: Setup Playwright
  run: |
    pip install playwright
    playwright install chromium

- name: Run tests with PDF generation
  run: |
    python main.py --facility-data test_data.csv --model-data test_model.csv
```

### GitLab CI

```yaml
test_pdf_generation:
  script:
    - pip install playwright
    - playwright install chromium
    - python main.py --facility-data test_data.csv --model-data test_model.csv
```

## Browser Cache Location

Playwright stores browsers in:
- **Linux/macOS**: `~/.cache/ms-playwright/`
- **Windows**: `%USERPROFILE%\AppData\Local\ms-playwright\`

You can set a custom location:
```bash
export PLAYWRIGHT_BROWSERS_PATH=/custom/path
```

## Security Considerations

For production environments:
- Use `--disable-dev-shm-usage` for container environments
- Consider running in a sandboxed environment
- Monitor disk space usage for browser cache
- Regular updates: `playwright install chromium --force`

## Support

If you encounter issues:
1. Check [Playwright Python Documentation](https://playwright.dev/python/)
2. Review system logs in `logs/workforce_analytics.log`
3. Run integration tests: `python test_system.py`
4. Enable debug logging for detailed diagnostics
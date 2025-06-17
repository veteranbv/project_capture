"""Security scanning for sensitive data detection."""
import re
from typing import List, NamedTuple, Pattern


class SecurityPattern(NamedTuple):
    """Represents a security pattern to detect."""
    name: str
    pattern: Pattern[str]
    severity: str  # 'high', 'medium', 'low'
    description: str


# Common patterns for sensitive data
SECURITY_PATTERNS: List[SecurityPattern] = [
    # API Keys and Tokens
    SecurityPattern(
        name="Generic API Key",
        pattern=re.compile(r'["\']?[Aa][Pp][Ii][_-]?[Kk][Ee][Yy]["\']?\s*[:=]\s*["\']?[\w\-\.]{20,}["\']?'),
        severity="high",
        description="Potential API key detected"
    ),
    SecurityPattern(
        name="AWS Access Key",
        pattern=re.compile(r'AKIA[0-9A-Z]{16}'),
        severity="high",
        description="AWS Access Key ID detected"
    ),
    SecurityPattern(
        name="AWS Secret Key",
        pattern=re.compile(r'["\']?aws[_-]?secret[_-]?access[_-]?key["\']?\s*[:=]\s*["\']?[A-Za-z0-9/+=]{40}["\']?', re.IGNORECASE),
        severity="high",
        description="AWS Secret Access Key detected"
    ),
    SecurityPattern(
        name="GitHub Token",
        pattern=re.compile(r'ghp_[0-9a-zA-Z]{36}|github_pat_[0-9a-zA-Z]{22}_[0-9a-zA-Z]{59}'),
        severity="high",
        description="GitHub Personal Access Token detected"
    ),
    SecurityPattern(
        name="Generic Secret",
        pattern=re.compile(r'["\']?[Ss][Ee][Cc][Rr][Ee][Tt]["\']?\s*[:=]\s*["\']?[\w\-\.]{8,}["\']?'),
        severity="medium",
        description="Potential secret value detected"
    ),
    SecurityPattern(
        name="Private Key",
        pattern=re.compile(r'-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----'),
        severity="high",
        description="Private key file detected"
    ),
    # Database Connection Strings
    SecurityPattern(
        name="Database URL",
        pattern=re.compile(r'(mongodb|postgres|postgresql|mysql|redis)://[^\s]+:[^\s]+@[^\s]+'),
        severity="high",
        description="Database connection string with credentials detected"
    ),
    # URLs with embedded credentials
    SecurityPattern(
        name="URL with Password",
        pattern=re.compile(r'https?://[^:]+:[^@]+@[^\s]+'),
        severity="high",
        description="URL containing embedded credentials detected"
    ),
]


def scan_content(content: str, filename: str = "") -> List[tuple[SecurityPattern, int]]:
    """Scan content for security patterns.
    
    Args:
        content: The text content to scan
        filename: Optional filename for context
        
    Returns:
        List of (pattern, line_number) tuples for detected issues
    """
    detected = []
    lines = content.split('\n')
    
    # Skip files that are likely to have false positives
    if filename:
        skip_extensions = {'.md', '.rst', '.txt', '.json', '.lock'}
        if any(filename.endswith(ext) for ext in skip_extensions):
            return detected
    
    for i, line in enumerate(lines, 1):
        # Skip commented lines
        stripped = line.strip()
        if stripped.startswith('#') or stripped.startswith('//'):
            continue
            
        for pattern in SECURITY_PATTERNS:
            if pattern.pattern.search(line):
                detected.append((pattern, i))
    
    return detected


def format_security_report(detections: List[tuple[SecurityPattern, int, str]]) -> str:
    """Format security detections into a readable report.
    
    Args:
        detections: List of (pattern, line_number, filename) tuples
        
    Returns:
        Formatted security report
    """
    if not detections:
        return "No security issues detected."
    
    report = ["## Security Scan Results\n"]
    report.append(f"Found {len(detections)} potential security issue(s):\n")
    
    # Group by severity
    by_severity = {'high': [], 'medium': [], 'low': []}
    for pattern, line, filename in detections:
        by_severity[pattern.severity].append((pattern, line, filename))
    
    for severity in ['high', 'medium', 'low']:
        items = by_severity[severity]
        if items:
            report.append(f"\n### {severity.upper()} Severity ({len(items)} issues)\n")
            for pattern, line, filename in items:
                report.append(f"- **{pattern.name}** in `{filename}` at line {line}")
                report.append(f"  {pattern.description}\n")
    
    return '\n'.join(report)
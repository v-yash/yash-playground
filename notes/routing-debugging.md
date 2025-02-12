Sure! Here’s a summary of the commands we used (and some additional useful ones) to debug routing and connectivity issues related to domain routing, ALB, HAProxy, and CDN. These commands will help you troubleshoot similar issues in the future.

---

### **1. Checking HTTP/HTTPS Response Headers**
These commands help to inspect response headers, status codes, and the routing path.

#### **Curl Commands Used:**
```bash
# Basic header check
curl -I https://example.com

# Check with specific Host header (useful when testing ALB and HAProxy routing)
curl -I -H "Host: your-domain.com" http://your-alb-url

# Bypass SSL verification (useful for ALB/HAProxy SSL issues)
curl -I -H "Host: your-domain.com" --insecure https://your-alb-url

# Force cache bypass to see fresh content
curl -I -H "Host: your-domain.com" -H "Cache-Control: no-cache" -H "Pragma: no-cache" https://your-cdn-url

# Verbose output to inspect SSL handshake and request flow
curl -Iv https://example.com

# Specify request method (e.g., GET, POST)
curl -X GET -I https://example.com

# Test backend application response directly
curl -I http://backend-server-ip:port
```

---

### **2. Checking ALB Routing and Health**
These commands help verify if ALB is routing traffic correctly and if the backend targets are healthy.

```bash
# Check ALB target health using AWS CLI
aws elbv2 describe-target-health --target-group-arn <target-group-arn>

# Check ALB rules and listeners
aws elbv2 describe-listeners --load-balancer-arn <alb-arn>
aws elbv2 describe-rules --listener-arn <listener-arn>

# Test ALB access logs (if enabled)
aws s3 ls s3://your-alb-logs-bucket/ --recursive | grep "2025-01-24"
```

---

### **3. Checking HAProxy Configuration**
Use these commands to check if HAProxy is processing requests correctly.

```bash
# Check HAProxy logs for errors
sudo tail -f /var/log/haproxy.log

# Validate HAProxy config syntax
haproxy -c -f /etc/haproxy/haproxy.cfg

# Show live statistics of HAProxy
echo "show stat" | sudo socat /var/lib/haproxy/stats stdio

# Check HAProxy frontend/backend configurations
cat /etc/haproxy/haproxy.cfg | grep -E "frontend|backend"
```

---

### **4. Checking CloudFront (CDN) Behavior**
These commands help analyze CloudFront cache behavior and origin routing.

```bash
# Check CloudFront distribution details
aws cloudfront get-distribution --id <distribution-id>

# Invalidate CloudFront cache
aws cloudfront create-invalidation --distribution-id <distribution-id> --paths "/*"

# Test if CloudFront is caching correctly
curl -I -H "Cache-Control: no-cache" https://your-cloudfront-url

# Analyze CloudFront logs (if enabled)
aws s3 ls s3://your-cloudfront-logs-bucket/ --recursive | grep "2025-01-24"
```

---

### **5. DNS Resolution and Connectivity Testing**
These commands help verify domain resolution and connectivity.

```bash
# Check DNS resolution (which IP the domain resolves to)
nslookup your-domain.com
dig your-domain.com +short

# Test connectivity to specific port
telnet your-domain.com 443

# Check for packet loss and latency
ping your-domain.com

# Check all DNS records (A, CNAME, MX, etc.)
dig your-domain.com ANY

# Trace route to the destination to check routing path
traceroute your-domain.com
```

---

### **6. Checking Firewall and Network Access**
Use these to verify network access permissions.

```bash
# Check if a port is open
nc -zv your-server-ip 443

# Check security group rules (if on AWS)
aws ec2 describe-security-groups --group-ids <sg-id>

# List open ports on a machine
sudo netstat -tuln
```

---

### **7. Debugging SSL Issues**
SSL/TLS issues can cause failures in routing. Use these commands to debug.

```bash
# Check SSL certificate details
openssl s_client -connect your-domain.com:443

# View certificate expiration
echo | openssl s_client -servername your-domain.com -connect your-domain.com:443 2>/dev/null | openssl x509 -noout -dates

# Test SSL/TLS handshake
openssl s_client -connect your-alb-url:443 -servername your-domain.com
```

---

Keeping these commands handy will help you troubleshoot and debug similar routing and connectivity issues efficiently in the future.

Let me know if you need any more details! 😊
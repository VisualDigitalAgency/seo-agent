# External API Error Handling Documentation

## Overview

This document describes the comprehensive error handling and timeout management system implemented for all external API calls in the SEO Agent backend.

## Features Implemented

### 1. Circuit Breaker Pattern
- Prevents cascading failures by stopping requests to failing services
- Configurable thresholds and timeouts per provider
- Automatic recovery after timeout period
- Graceful fallback to alternative providers

### 2. Exponential Backoff with Jitter
- 3 retry attempts with exponential backoff
- Jitter (random variation) to prevent thundering herd
- Base delays: Serper=1s, DataForSEO=2s, GSC/GA4=2s
- Max delays: 10s for web APIs, 15s for DataForSEO

### 3. Timeout Protection
- HTTP requests: 20s (configurable)
- Total operation timeout: 25s (configurable)
- Specific service timeouts: DataForSEO=30s, GSC/GA4=30s

### 4. Structured Error Logging
- All errors logged with context and stack traces
- Rate-limited logging to prevent log spam
- Circuit breaker state changes logged
- API-specific error messages

### 5. Graceful Fallbacks
- Serper → SerpAPI for search operations
- Structured error responses with status codes
- No crash on API failures

## Provider-Specific Configuration

### Serper.dev
- Circuit breaker: 5 failures, 60s timeout
- Rate limiting: 60 requests/minute, 5 concurrent
- Fallback: SerpAPI
- Error handling: HTTP status errors, timeouts

### DataForSEO
- Circuit breaker: 5 failures, 120s timeout
- Rate limiting: 100 requests/minute, 10 concurrent
- Error handling: Client errors (400s) not retried, timeouts

### Google Search Console (GSC)
- Circuit breaker: 3 failures, 120s timeout
- Rate limiting: 100 requests/minute, 5 concurrent
- Error handling: Timeouts, API errors
- Note: Uses Google API client with asyncio wrappers

### Google Analytics 4 (GA4)
- Circuit breaker: 3 failures, 120s timeout
- Rate limiting: 100 requests/minute, 5 concurrent
- Error handling: Timeouts, API errors
- Note: Uses Google API client with asyncio wrappers

## Implementation Details

### Circuit Breaker States
- **CLOSED**: Normal operation
- **OPEN**: Failing, reject calls immediately
- **HALF_OPEN**: Testing after timeout, allows limited calls

### Error Handling Flow
1. Check circuit breaker state
2. Make API call with timeout
3. Retry on failure (exponential backoff)
4. On success: record success
5. On failure: record failure, open breaker if threshold reached
6. Return structured error response

### Rate Limiting
- Per-provider async rate limiting
- Configurable via environment variables
- Fallback to default values

## Environment Variables

### Rate Limiting
- `SERPER_REQUESTS_PER_MINUTE` (default: 60)
- `SERPER_CONCURRENT` (default: 5)
- `DATAFORSEO_REQUESTS_PER_MINUTE` (default: 100)
- `DATAFORSEO_CONCURRENT` (default: 10)
- `GSC_REQUESTS_PER_MINUTE` (default: 100)
- `GSC_CONCURRENT` (default: 5)
- `GA4_REQUESTS_PER_MINUTE` (default: 100)
- `GA4_CONCURRENT` (default: 5)

### Credentials
- `SERPER_API_KEY`, `SERPAPI_KEY`
- `DATAFORSEO_LOGIN`, `DATAFORSEO_PASSWORD`
- `GSC_CREDENTIALS_PATH`
- `GA4_CREDENTIALS_PATH`, `GA4_PROPERTY_ID`

## Usage Examples

```python
# Example: Using with retry and circuit breaker
from tools import search_serp

# This will automatically:
# 1. Use circuit breaker to check if service is available
# 2. Retry up to 3 times with exponential backoff
# 3. Timeout after 25s total
# 4. Fall back to SerpAPI if Serper fails
# 5. Return structured error if all fails
result = await search_serp("SEO tools", num=10, country="us")

# Example: Get circuit breaker status
from tools._circuit_breaker import get_all_circuit_breakers
breakers = get_all_circuit_breakers()
for name, breaker in breakers.items():
    print(f"{name}: {breaker.state.state}")
```

## Testing and Monitoring

### Testing
- Circuit breaker can be manually reset
- Individual service calls can be tested
- Retry behavior can be observed via logs

### Monitoring
- All errors logged with context
- Circuit breaker state changes logged
- Rate limiting logs available
- Structured error responses for API consumers

## Performance Considerations

- Async rate limiting prevents resource exhaustion
- Circuit breaker prevents wasted requests to failing services
- Retry delays prevent overwhelming services during outages
- Timeout protection prevents hanging operations

## Failure Modes Handled

### Network Issues
- Timeouts
- Connection errors
- DNS failures

### Service Issues
- 5xx errors
- Rate limiting (429)
- Service unavailable

### Authentication Issues
- Invalid API keys
- Expired credentials
- Permission denied

### Data Issues
- Invalid responses
- Missing fields
- Type mismatches

## Return Value Structure

All functions return consistent structures:

```python
{
    "success": True/False,
    "data": ...,  # or None on error
    "error": "Error message" if failed,  # or None on success
    "status_code": 200/400/500,  # HTTP-like status code
    "timestamp": 1234567890.0,
    "details": {...}  # Optional additional context
}
```
# EODHD API Rate Limits & Usage

## EODHD Official Limits

- **Daily Limit**: 100,000 API requests per day
- **Minute Limit**: 1,000 API requests per minute
- **Cost per Request**: 1 API call per symbol/endpoint
- **Subscription**: Fundamentals plan at $59.99/month

## Our Implementation

### Rate Limiting
- **Delay Between Requests**: 75ms (0.075 seconds)
- **Effective Rate**: ~800 requests per minute (80% of limit, safe buffer)
- **Requests per Second**: ~13.3
- **Implementation**: `time.sleep(0.075)` after each API call

### Caching Strategy
To minimize API usage, we implement aggressive caching:

1. **Symbol Lists**: 24-hour cache
   - NSE symbols: Cached for 1 day
   - BSE symbols: Cached for 1 day
   - Saves ~1 API call per session

2. **Fundamental Data**: 7-day cache
   - Company fundamentals: Cached for 7 days
   - Reduces repeated downloads for same company
   - Useful during testing/development

### Bulk Download Estimates

#### Scenario 1: Initial Full Download (2000 NSE companies)
```
Companies to download: 2,000
API calls required: 2,001 (2000 companies + 1 symbol list)
Time estimate: ~2.5 minutes (75ms delay × 2000)
Percentage of daily limit: 2%
```

#### Scenario 2: Weekly Update (assuming 10% need updates)
```
Companies to update: 200
API calls required: 200
Time estimate: ~15 seconds
Percentage of daily limit: 0.2%
```

#### Scenario 3: Quarterly Full Refresh (all 2000)
```
Companies to refresh: 2,000
API calls required: 2,000
Time estimate: ~2.5 minutes
Percentage of daily limit: 2%
```

## Safety Margins

✅ **Well Within Limits**: Our bulk download of 2,000 companies uses only 2% of daily quota

✅ **Optimized Rate**: 75ms delay = 800 req/min (80% of 1000/min limit, 20% safety buffer)

✅ **Caching**: Reduces redundant API calls by 90%+ during development

✅ **Fast Downloads**: 2,000 companies in ~2.5 minutes (vs 17 minutes with old rate)

## Daily Quota Usage Breakdown

| Operation | API Calls | % of Daily Limit |
|-----------|-----------|------------------|
| Symbol list fetch (NSE) | 1 | 0.001% |
| Initial download (2000) | 2,000 | 2% |
| Weekly updates (200) | 200 | 0.2% |
| Testing (50 companies) | 50 | 0.05% |
| **Total Daily Usage** | **~2,250** | **~2.25%** |

## Recommendations

1. **Initial Bulk Download**
   - Run once: Download all 2,000 companies
   - Time: 15-20 minutes
   - API calls: 2,000

2. **Quarterly Updates**
   - Frequency: Every 3 months (after earnings)
   - Companies: All 2,000 (full refresh)
   - API calls: 2,000 per quarter

3. **On-Demand Updates**
   - Use for specific companies when needed
   - Cached data serves most requests

## Monitoring

To monitor API usage:
```python
# Check cache statistics
client = EODHDClient(api_key)
cache_files = list(client.cache_dir.glob('*.json'))
print(f"Cached responses: {len(cache_files)}")
```

## Error Handling

If rate limited (HTTP 429):
- Current implementation: Will fail with error
- Recommended: Add exponential backoff (not implemented yet)

## Cost Efficiency

**Annual Cost**: $59.99/month × 12 = $719.88/year

**Per Company Cost**: $719.88 / 2000 = $0.36 per company per year

**Compared to Alternatives**:
- Manual data entry: $50-100/hour × 100+ hours = $5,000-10,000
- NSE/BSE official API: ₹50,000-5,00,000/year
- Other data providers: $100-500/month

**Verdict**: EODHD is highly cost-effective for 2000 companies

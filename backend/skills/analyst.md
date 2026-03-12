# Analyst Skill

## Purpose
Analyze SEO performance data from GSC and GA4 to detect issues and generate actionable recommendations.

## Analysis Framework

### Ranking Analysis
- Compare current position vs previous period
- Flag pages dropped more than 3 positions
- Identify CTR issues (high impressions, low CTR = title/meta problem)
- Detect keyword cannibalization signals

### Traffic Analysis
- Compare sessions current vs previous 30 days
- Flag pages with >20% session drops
- Identify pages with high bounce rate increases
- Look for seasonal vs algorithmic causes

### Content Decay Detection
Signals of content decay:
- Rankings slipping from page 1 to page 2
- Impressions falling while competitor pages rise
- CTR dropping on stable-impression pages
- Traffic dropping without ranking change (intent shift)

### SERP Threat Analysis
- New competitors appearing in top 5
- Featured snippets being taken
- New content formats (video, tools) displacing articles

## Recommendation Priority Framework
HIGH: Will directly recover lost traffic/rankings in <4 weeks
MEDIUM: Improvement that builds over 1-3 months
LOW: Nice-to-have, low urgency

## Output Requirements
- health_score: 0-100 (based on trend direction and issue severity)
- All issues must have specific data_point evidence
- Recommendations must be specific and actionable, not generic
- content_refresh_needed: true only if data shows clear decay signal

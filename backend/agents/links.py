"""Links Agent — Topic cluster + internal linking strategy"""
from .base import BaseAgent
import json


class LinksAgent(BaseAgent):

    def build_cluster(self, context):
        self.log("Links Agent: Building topic cluster and internal link map...")
        skill = self.load_skill('internal_linking')
        kw = context.get('keyword_research', {})
        onpage = context.get('onpage_optimization', {})

        domain = self.pipeline.domain or 'yoursite.com'

        prompt = f"""
{skill}

PRIMARY TOPIC: {self.pipeline.task}
DOMAIN: {domain}
TARGET AUDIENCE: {self.pipeline.audience or 'General'}
PRIMARY KEYWORD: {kw.get('primary', self.pipeline.task)}
SECONDARY KEYWORDS: {', '.join(kw.get('secondary', []))}

ON-PAGE RECOMMENDATIONS:
{json.dumps(onpage.get('recommended_internal_links', []), indent=2)}

Build a complete topic cluster and internal linking strategy. Return JSON:
{{
  "pillar_page": {{
    "topic": "main pillar topic",
    "url": "/{domain}/pillar-page-slug",
    "target_keyword": "primary kw"
  }},
  "cluster_pages": [
    {{
      "topic": "cluster topic 1",
      "target_keyword": "keyword",
      "url_slug": "slug",
      "relationship": "supports pillar by covering X",
      "priority": "high|medium|low"
    }}
  ],
  "internal_links_for_this_page": [
    {{
      "anchor_text": "exact anchor text",
      "link_to": "url or topic",
      "context": "where in the article to place it"
    }}
  ],
  "backlink_opportunities": [
    {{
      "type": "guest post|resource page|broken link",
      "target_site_type": "e.g. fintech blogs",
      "angle": "pitch angle"
    }}
  ],
  "topical_authority_map": {{
    "core_topic": "{self.pipeline.task}",
    "subtopics": ["subtopic1", "subtopic2", "subtopic3"],
    "coverage_gaps": ["gap1", "gap2"]
  }}
}}
"""
        result = self.call_claude(
            system_prompt="You are an SEO strategist specializing in topic clusters and internal linking architecture.",
            user_prompt=prompt
        )
        self.log(f"Link strategy built. Cluster pages: {len(result.get('cluster_pages', []))}")
        return result

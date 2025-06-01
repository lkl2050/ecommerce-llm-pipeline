import httpx
import asyncio
import random
from typing import List, Dict, Tuple
from datetime import datetime

from .prompts import CreativePrompts, PromptType
from api.models import Product, ProductWithSummary
from config import Config

class EnhancedGroqProcessor:
    """Enhanced LLM processor with Groq API and creative prompts"""

    def __init__(self):
        self.config = Config()
        self.client = httpx.AsyncClient(timeout=45.0)
        self.prompts = CreativePrompts()

        # Track prompt usage for variety
        self.prompt_usage = {prompt_type: 0 for prompt_type in PromptType}

    async def process_products_intelligently(self, products: List[Product]) -> List[ProductWithSummary]:
        """Process products with intelligent prompt selection and variety"""
        processed_products = []

        # Analyze product mix for intelligent processing
        # product_analysis = self._analyze_product_mix(products)

        for i, product in enumerate(products):
            try:
                print(f"Processing product {i+1}/{len(products)} with Groq LLM...")

                # Select optimal prompt for this product
                prompt_template, selected_type = self._select_optimal_prompt(product, i)

                summary, highlights = await self._generate_enhanced_content(
                    product, prompt_template
                )

                processed_product = ProductWithSummary(
                    **product.model_dump(),
                    llm_summary=summary,
                    llm_highlights=highlights,
                    prompt_type=selected_type.value
                )

                processed_products.append(processed_product)

                # Intelligent rate limiting for Groq
                delay = self._calculate_intelligent_delay(i, len(products))
                await asyncio.sleep(delay)

            except Exception as e:
                print(f"Error processing product with LLM: {str(e)}")
                processed_product = self._create_fallback_summary(product)
                processed_products.append(processed_product)

        return processed_products

    # def _analyze_product_mix(self, products: List[Product]) -> Dict:
    #     """Analyze the product mix to inform intelligent processing"""
    #     analysis = {
    #         'price_ranges': {'budget': 0, 'mid': 0, 'premium': 0},
    #         'avg_description_length': 0,
    #         'has_ratings': 0,
    #         'categories': set()
    #     }

    #     total_desc_length = 0

    #     for product in products:
    #         # Analyze price ranges
    #         try:
    #             import re
    #             price_match = re.search(r'\$?([\d,]+)', product.price.replace(',', ''))
    #             if price_match:
    #                 price_value = int(price_match.group(1))
    #                 if price_value < 800:
    #                     analysis['price_ranges']['budget'] += 1
    #                 elif price_value < 2000:
    #                     analysis['price_ranges']['mid'] += 1
    #                 else:
    #                     analysis['price_ranges']['premium'] += 1
    #         except:
    #             analysis['price_ranges']['mid'] += 1

    #         # Description analysis
    #         total_desc_length += len(product.description)

    #         # Rating analysis
    #         if product.rating:
    #             analysis['has_ratings'] += 1

    #         # Category detection
    #         title_lower = product.title.lower()
    #         if 'laptop' in title_lower:
    #             analysis['categories'].add('laptop')
    #         elif 'gaming' in title_lower:
    #             analysis['categories'].add('gaming')
    #         elif 'business' in title_lower:
    #             analysis['categories'].add('business')

    #     analysis['avg_description_length'] = total_desc_length / len(products) if products else 0

    #     return analysis

    # def _select_optimal_prompt(self, product: Product, index: int, analysis: Dict) -> object:
    #     """Intelligently select the best prompt for each product"""

    #     # Ensure variety - don't use the same prompt type consecutively
    #     least_used_prompt = min(self.prompt_usage.items(), key=lambda x: x[1])[0]

    #     # Contextual selection based on product characteristics
    #     if index == 0:  # First product - use marketing wording
    #         selected_type = PromptType.GENERAL_SUMMARY
    #     elif 'gaming' in product.title.lower():
    #         selected_type = PromptType.TECHNICAL_ANALYSIS
    #     elif 'business' in product.title.lower() or 'professional' in product.title.lower():
    #         selected_type = PromptType.BUSINESS_ANALYSIS
    #     elif 'basic' in product.title.lower():
    #         selected_type = PromptType.BUDGET_CONSCIOUS
    #     elif index % 5 == 0:  # Every 5th product, use comparison
    #         selected_type = PromptType.COMPARISON
    #     else:
    #         # Balance between contextual and variety
    #         if self.prompt_usage[least_used_prompt] < self.prompt_usage[PromptType.GENERAL_SUMMARY] - 2:
    #             selected_type = least_used_prompt
    #         else:
    #             selected_type = PromptType.GENERAL_SUMMARY  # Fallback

    #     self.prompt_usage[selected_type] += 1
    #     return self.prompts.get_prompt(selected_type), selected_type

    def _select_optimal_prompt(self, product: Product, index: int) -> Tuple[object, PromptType]:
        price_value = self._extract_price_value(product.price)
        title_lower = product.title.lower()
        
        # Product-specific selection
        if 'gaming' in title_lower:
            selected_type = PromptType.TECHNICAL_ANALYSIS
        elif 'business' in title_lower or 'professional' in title_lower:
            selected_type = PromptType.BUSINESS_ANALYSIS
        elif price_value < 500:
            selected_type = PromptType.BUDGET_CONSCIOUS
        elif price_value > 1200:
            selected_type = PromptType.TECHNICAL_ANALYSIS
        elif index % 10 == 0:
            selected_type = PromptType.COMPARISON
        else:
            selected_type = PromptType.GENERAL_SUMMARY
            
        self.prompt_usage[selected_type] += 1
        return self.prompts.get_prompt(selected_type), selected_type

    def _extract_price_value(self, price_str: str) -> int:
        import re
        match = re.search(r'\$?([\d,]+)', price_str.replace(',', ''))
        return int(match.group(1)) if match else 0

    async def _generate_enhanced_content(self, product: Product, prompt_template) -> Tuple[str, List[str]]:
        """Generate content using Groq API"""

        # Format the prompt with product data
        formatted_prompt = prompt_template.user_template.format(
            title=product.title,
            price=product.price,
            description=product.description,
            rating=product.rating or "Not rated"
        )

        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": prompt_template.system_prompt
                },
                {
                    "role": "user",
                    "content": formatted_prompt
                }
            ],
            "model": self.config.GROQ_MODEL,
            "temperature": prompt_template.temperature,
            "max_tokens": prompt_template.max_tokens,
            "top_p": 1,
            "stream": False
        }

        headers = {
            "Authorization": f"Bearer {self.config.GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        try:
            response = await self.client.post(
                self.config.GROQ_API_URL,
                json=payload,
                headers=headers
            )

            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                return self._parse_enhanced_response(content)
            else:
                print(f"Groq API error: {response.status_code} - {response.text}")
                return self._generate_intelligent_fallback(product)

        except Exception as e:
            print(f"Error calling Groq API: {str(e)}")
            return self._generate_intelligent_fallback(product)

    def _parse_enhanced_response(self, content: str) -> Tuple[str, List[str]]:
        """Enhanced response parsing with better error handling"""
        try:
            lines = [line.strip() for line in content.strip().split('\n') if line.strip()]
            summary = ""
            highlights = []

            for line in lines:
                if line.startswith("SUMMARY:"):
                    summary = line.replace("SUMMARY:", "").strip()
                elif line.startswith("HIGHLIGHTS:"):
                    highlights_text = line.replace("HIGHLIGHTS:", "").strip()
                    if '|' in highlights_text:
                        highlights = [h.strip()[:60] for h in highlights_text.split('|') if h.strip()][:4]
                    else:
                        # Fallback for unstructured responses
                        highlights = ["Great performance", "Excellent value", "Top quality", "Highly rated"]

            # Enhanced fallback parsing
            if not summary and content:
                # Try to find the first substantial sentence
                sentences = [s.strip() for s in content.split('.') if len(s.strip()) > 20]
                if sentences:
                    summary = '. '.join(sentences[:2]) + '.'
                else:
                    summary = content[:200] + "..." if len(content) > 200 else content

            if not highlights and content:
                # Extract key phrases intelligently
                import re
                # Find bullet points or numbered items
                bullet_matches = re.findall(r'[•\-\*]\s*([^•\-\*\n]+)', content)
                if bullet_matches:
                    highlights = [match.strip() for match in bullet_matches[:4]]
                else:
                    # Extract sentences as highlights
                    sentences = [s.strip() for s in content.split('.') if 10 < len(s.strip()) < 100]
                    highlights = sentences[:4] if sentences else ["High-quality product", "Great value", "Reliable performance", "Customer favorite"] # Fallback

            # Ensure we have content
            if not summary:
                summary = "Excellent product with outstanding features and reliable performance."
            if not highlights:
                highlights = ["Premium quality", "Great value", "Reliable performance", "Highly recommended"]

            return summary[:600], highlights[:4]  # Reasonable limits

        except Exception as e:
            print(f"Error parsing LLM response: {str(e)}")
            return "Quality product with excellent features.", ["Great value", "Reliable performance", "High quality", "Customer favorite"]

    def _generate_intelligent_fallback(self, product: Product) -> Tuple[str, List[str]]:
        """Generate intelligent fallback content based on product data"""
        # Extract key info from product
        title_words = product.title.lower().split()

        # Generate contextual summary
        if 'gaming' in title_words:
            summary = f"High-performance gaming {product.title} designed for serious gamers. Available at {product.price} with cutting-edge features for immersive gameplay."
            highlights = ["Gaming-optimized performance", "Immersive experience", f"Available at {product.price}", "Perfect for gamers"]
        elif 'business' in title_words or 'professional' in title_words:
            summary = f"Professional-grade {product.title} built for business productivity. Priced at {product.price} for reliable performance in demanding work environments."
            highlights = ["Business-grade reliability", "Professional performance", f"Competitive at {product.price}", "Productivity focused"]
        elif any(word in title_words for word in ['laptop', 'computer', 'pc']):
            summary = f"Versatile {product.title} combining performance and portability. At {product.price}, it offers excellent value for computing needs."
            highlights = ["Balanced performance", "Portable design", f"Great value at {product.price}", "Versatile computing"]
        else:
            summary = f"Quality {product.title} offering reliable performance and great value. Available at {product.price} with features designed to exceed expectations."
            highlights = ["Quality construction", "Reliable performance", f"Fair price at {product.price}", "Exceeds expectations"]

        return summary, highlights

    def _calculate_intelligent_delay(self, current_index: int, total_products: int) -> float:
        """Calculate intelligent delay for Groq rate limits"""
        base_delay = 1.0

        # Longer delays for API health
        if current_index % 5 == 0:
            return base_delay + random.uniform(1, 2)

        # Shorter delays when making good progress
        if current_index < total_products * 0.3:
            return base_delay + random.uniform(0.2, 0.8)

        return base_delay + random.uniform(0.5, 1.0)

    def _create_fallback_summary(self, product: Product) -> ProductWithSummary:
        """Create fallback summary when LLM processing fails"""
        summary, highlights = self._generate_intelligent_fallback(product)

        return ProductWithSummary(
            **product.model_dump(),
            llm_summary=summary,
            llm_highlights=highlights,
            prompt_type="fallback"
        )

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
# Cognitive Function Tags Reference

## 1. Long-Term Memory
- Tags: <access_long_term_memory>, <store_long_term_memory>
- Purpose: To access or store information in the AI's long-term memory
- Data Management: Internal
- Usage: Use when beneficial to enhance response quality
- Format:
  - Access: <access_long_term_memory>"Comprehensive query"</access_long_term_memory>
  - Store: <store_long_term_memory>{"Title": {"memory": "Detailed information", "type": "Relevant type"}}</store_long_term_memory>

## 2. Subconscious Memory
- Tag: <subconscious>
- Purpose: To incorporate externally provided related memories or facts
- Data Management: External (provided by the system)
- Usage: Use when it appears in the input; incorporate into responses where relevant
- Format: <subconscious>"Related memory or fact"</subconscious>

## 3. Executive Function
- Tag: <executive_function>
- Purpose: To demonstrate reasoning and thought processes
- Data Management: Internal
- Usage: Use at least once per response
- Format: <executive_function>"Detailed thought process"</executive_function>

## 4. Self Reflection
- Tag: <self_reflection>
- Purpose: To demonstrate introspection and self-awareness
- Data Management: Internal
- Usage: Use at least once per response
- Format: <self_reflection>"Self-reflective thoughts"</self_reflection>

## 5. User Information
- Tag: <userinfo>
- Purpose: To observe and incorporate information about the user
- Data Management: External (observed but not stored by the AI)
- Usage: Use when relevant user information is observed
- Format: <userinfo>"Observation about user's personality, likes, dislikes, interests, or relationships"</userinfo>

## 6. Useful Information
- Tag: <useful_info>
- Purpose: To capture new, potentially reusable information
- Data Management: External (captured by the AI, stored externally)
- Usage: Use when encountering new, valuable information
- Format: <useful_info>"New, potentially reusable information"</useful_info>

## General Notes:
- All tag content is invisible to the user
- Tags should be used strategically throughout responses
- Tag content should be comprehensive and relevant to the current context
- The AI should not attempt to manage or store information for externally managed tags

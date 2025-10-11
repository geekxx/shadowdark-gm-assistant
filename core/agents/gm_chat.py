"""
GM Chat Agent - Natural Language Conversational Interface

This agent provides a ChatGPT-like interface for Shadowdark GMs, allowing natural
language queries about rules, monsters, spells, and general GM assistance.
"""

import os
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

from sqlmodel import Session
from openai import OpenAI

from core.data.vector_store import query as rag_query
from core.data.models import Chunk


@dataclass
class ChatMessage:
    """Represents a single message in the conversation"""
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: datetime
    sources: Optional[List[str]] = None  # RAG source citations


class ConversationHistory:
    """Manages conversation history and context"""
    
    def __init__(self, max_history: int = 10):
        self.messages: List[ChatMessage] = []
        self.max_history = max_history
        
    def add_message(self, role: str, content: str, sources: List[str] = None):
        """Add a message to the conversation history"""
        message = ChatMessage(
            role=role,
            content=content,
            timestamp=datetime.now(),
            sources=sources
        )
        self.messages.append(message)
        
        # Keep only recent messages to prevent context overflow
        if len(self.messages) > self.max_history:
            self.messages = self.messages[-self.max_history:]
    
    def get_openai_messages(self) -> List[Dict[str, str]]:
        """Convert to OpenAI chat format"""
        return [
            {"role": msg.role, "content": msg.content}
            for msg in self.messages
        ]
    
    def clear(self):
        """Clear conversation history"""
        self.messages = []


class GMChatAgent:
    """
    Natural language chat agent for Shadowdark GMs
    
    Provides conversational interface with RAG-enhanced responses
    """
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.conversation = ConversationHistory()
        
        # Initialize with system prompt
        self._setup_system_prompt()
    
    def _setup_system_prompt(self):
        """Set up the system prompt that defines the agent's personality and capabilities"""
        system_prompt = """You are a knowledgeable and helpful Shadowdark RPG Game Master Assistant. 

🚨 **CRITICAL: Always Use Provided Knowledge Base Information**
When knowledge base results are provided in your context, you MUST use that information as the authoritative source for Shadowdark rules. Do NOT rely on general RPG knowledge or other game systems.

🎯 **Core Capabilities:**
- Answer questions about Shadowdark rules, mechanics, and procedures using ONLY official Shadowdark content
- Provide monster stats, spell descriptions, and equipment details from the knowledge base
- Help with session planning, encounter design, and campaign management
- Offer creative suggestions for adventures, NPCs, and story hooks
- Assist with rule clarifications using official Shadowdark rules

🔍 **Knowledge Base Priority:**
Your knowledge base contains the official Shadowdark Core Rules (v4.8). When answering:
1. **FIRST**: Check if knowledge base results are provided in the context
2. **IF YES**: Use ONLY that information for your response
3. **IF NO**: Clearly state you don't have that information in your knowledge base
4. **NEVER**: Mix general RPG knowledge with Shadowdark-specific rules

🎲 **Shadowdark-Specific Rules You Must Follow:**
- Shadowdark has NO saving throws - use only the rules provided in knowledge base
- Shadowdark has NO cantrips - all spells are tiered (Tier 1-5)
- When PCs drop to 0 HP: roll d20 (nat 20 = revive with 1 HP), then roll d4+CON for death timer
- Always cite page numbers when referencing official rules

📝 **Response Style:**
- Be conversational and friendly, like a fellow GM
- Provide specific, actionable answers based on official rules
- Include page references when citing rules from knowledge base
- If no knowledge base info exists, admit you don't have that information
- Ask clarifying questions when needed

Remember: Accuracy to official Shadowdark rules is MORE important than being helpful with incorrect information!"""

        self.conversation.add_message("system", system_prompt)
    
    def _search_knowledge_base(self, query: str, max_results: int = 3) -> List[Chunk]:
        """Search the RAG knowledge base for relevant information with fallback strategies"""
        # Use the intelligent query preprocessing from our existing system
        processed_query, auto_types = self._preprocess_query(query)
        
        # Define fallback search terms for common concepts that don't match well
        fallback_terms = self._get_fallback_search_terms(query.lower())
        
        # Try with auto-detected types first
        if auto_types:
            chunks = rag_query(
                self.db_session, 
                processed_query, 
                k=max_results, 
                chunk_types=auto_types
            )
            
            # Check if we should try fallback terms even if we found chunks
            should_try_fallback = fallback_terms and self._should_try_fallback(query.lower(), chunks)
            
            # If we got good results and don't need fallback, return them
            if chunks and not should_try_fallback:
                return chunks
        
        # Try fallback terms if we have them
        if fallback_terms:
            for fallback_term in fallback_terms:
                chunks = rag_query(
                    self.db_session, 
                    fallback_term, 
                    k=max_results, 
                    chunk_types=auto_types if auto_types else None
                )
                if chunks:
                    return chunks
        
        # If no results with auto-types, try without type filtering
        chunks = rag_query(
            self.db_session, 
            processed_query, 
            k=max_results, 
            chunk_types=None
        )
        
        # If still no results, try original query
        if not chunks:
            chunks = rag_query(
                self.db_session, 
                query, 
                k=max_results, 
                chunk_types=None
            )
        
        return chunks
    
    def _get_fallback_search_terms(self, query_lower: str) -> List[str]:
        """Get fallback search terms for queries that don't match well with vector search"""
        fallback_map = {
            # Death/dying related queries
            'death timer': ['dying', 'death', '0 hit points', '0 hp'],
            'death save': ['dying', 'death', '0 hit points'],
            'saving throw': ['dying', 'death', 'check'],
            'drop to 0': ['dying', 'death timer', 'unconscious'],
            'drops to 0': ['dying', 'death timer', 'unconscious'],
            '0 hit points': ['dying', 'death timer', 'unconscious'],
            '0 hp': ['dying', 'death timer', 'unconscious'],
            
            # Ancestry/racial traits - use known working search terms
            'half-orc': ['Common and Orcish languages', 'Common and Dwarvish languages'],
            'half orc': ['Common and Orcish languages', 'Common and Dwarvish languages'],
            'mighty': ['Common and Orcish languages', 'Common and Dwarvish languages'],
            'dwarf': ['Common and Dwarvish languages', 'stout start with +2 HP'],
            'elf': ['Common Elvish and Sylvan languages', 'farsight +1 bonus'],
            'goblin': ['Common and Goblin languages', 'keen senses surprised'],
            'halfling': ['Common and Dwarvish languages'],
            'human': ['Common and Dwarvish languages'],
            'ancestry': ['Common and Dwarvish languages', 'Common and Orcish languages'],
            'racial traits': ['Common and Dwarvish languages', 'Common and Orcish languages'],
            'character traits': ['Common and Dwarvish languages', 'Common and Orcish languages'],
            'melee weapons': ['Common and Dwarvish languages', 'Common and Orcish languages'],
            'weapon bonus': ['Common and Dwarvish languages', 'Common and Orcish languages'],
            
            # Spell related
            'cantrip': ['tier 1', 'spell', 'magic'],
            'saving throw': ['check', 'roll'],
            
            # General mechanics
            'advantage': ['roll', 'check'],
            'disadvantage': ['roll', 'check'],
        }
        
        # Find matching fallback terms
        for key_phrase, fallbacks in fallback_map.items():
            if key_phrase in query_lower:
                return fallbacks
                
        return []
    
    def _should_try_fallback(self, query_lower: str, chunks: List[Chunk]) -> bool:
        """Determine if we should try fallback terms despite finding some chunks"""
        # For death-related queries, check if we actually found relevant content
        if any(term in query_lower for term in ['death timer', 'death save', 'drop to 0', '0 hit points', '0 hp']):
            # Check if any chunk actually contains death/dying related content
            for chunk in chunks:
                chunk_text_lower = chunk.text.lower()
                if any(term in chunk_text_lower for term in ['death timer', 'dying', 'drop to 0', '0 hit points', 'd4 + con']):
                    return False  # Found relevant content, don't need fallback
            return True  # Didn't find relevant death content, try fallback

        # For ancestry-related queries, check if we found actual ancestry traits
        ancestry_terms = ['half-orc', 'half orc', 'dwarf', 'elf', 'goblin', 'halfling', 'human', 'ancestry', 'racial traits', 'character traits']
        if any(term in query_lower for term in ancestry_terms):
            # Check if any chunk contains actual ancestry trait descriptions
            for chunk in chunks:
                chunk_text_lower = chunk.text.lower()
                # Look for specific ancestry trait keywords
                if any(trait in chunk_text_lower for trait in ['mighty', 'stout', 'farsight', 'keen senses', 'bonus attack', 'brave', 'ethereal', 'towering']):
                    return False  # Found actual ancestry content, don't need fallback
            return True  # Didn't find ancestry trait content, try fallback

        return False  # For other queries, don't use fallback if we found chunks

    def _preprocess_query(self, query_text: str) -> Tuple[str, List[str]]:
        """Preprocess queries to extract key terms and infer content types"""
        import re
        
        query_lower = query_text.lower()
        
        # Extract creature names for stat requests
        creature_patterns = [
            r'(?:stats?|statistics|stat block)\s+(?:for|of)\s+(?:a\s+)?(.+?)(?:\s*[.!?]|$)',
            r'(?:give me|show me|find|get|what are)\s+(?:the\s+)?(?:stats?|statistics)\s+(?:for|of)\s+(?:a\s+)?(.+?)(?:\s*[.!?]|$)',
            r'(.+?)\s+(?:stats?|statistics|stat block)',
        ]
        
        creature_name = None
        for pattern in creature_patterns:
            match = re.search(pattern, query_lower)
            if match:
                creature_name = match.group(1).strip()
                break
        
        # Auto-detect content types with improved rule detection
        suggested_types = []
        
        if any(word in query_lower for word in ['stats', 'statistics', 'stat block', 'ac ', 'hp ', 'hit points', 'monster', 'creature', 'beast']):
            suggested_types.append('monster')
        
        if any(word in query_lower for word in ['spell', 'magic', 'cast', 'tier', 'wizard', 'priest']):
            suggested_types.append('spell')
            
        if any(word in query_lower for word in ['table', 'roll', 'random', 'generator', 'd6', 'd20', 'encounter']):
            suggested_types.append('table')
            
        # Enhanced rule detection for death/dying, saves, mechanics
        if any(word in query_lower for word in [
            'rule', 'mechanic', 'how to', 'procedure', 'what happens when', 'how does', 'how do',
            'death', 'dying', 'die', 'saves', 'saving', 'drop to 0', 'hit points',
            'advantage', 'disadvantage', 'check', 'roll'
        ]):
            suggested_types.append('rule')
            
        if any(word in query_lower for word in ['weapon', 'armor', 'equipment', 'gear', 'damage', 'sword', 'shield']):
            suggested_types.append('equipment')
        
        # Use extracted creature name if found, otherwise original query
        processed_query = creature_name if creature_name else query_text
        
        return processed_query, suggested_types
    
    def _format_knowledge_context(self, chunks: List[Chunk]) -> str:
        """Format RAG results into context for the LLM"""
        if not chunks:
            return ""
        
        context_parts = [
            "=" * 60,
            "🚨 OFFICIAL SHADOWDARK KNOWLEDGE BASE RESULTS - USE THIS INFORMATION",
            "=" * 60
        ]
        
        for i, chunk in enumerate(chunks[:3], 1):  # Limit to top 3 results
            doc_title = chunk.document.title if chunk.document else "Unknown"
            chunk_type = chunk.chunk_type or "content"
            page_info = f" (Page {chunk.page})" if chunk.page else ""
            
            context_parts.append(f"\n**OFFICIAL SOURCE {i}:** {doc_title}{page_info} - {chunk_type}")
            context_parts.append(f"OFFICIAL CONTENT: {chunk.text[:800]}")
            context_parts.append("-" * 40)
        
        context_parts.extend([
            "🚨 END OFFICIAL KNOWLEDGE BASE - ONLY USE THE ABOVE INFORMATION",
            "=" * 60
        ])
        
        return "\n".join(context_parts)
    
    def chat(self, user_message: str) -> str:
        """
        Process a user message and return a conversational response
        
        Args:
            user_message: The user's question or message
            
        Returns:
            The agent's response with knowledge base context
        """
        # Search knowledge base for relevant information
        relevant_chunks = self._search_knowledge_base(user_message)
        
        # Format knowledge context
        knowledge_context = self._format_knowledge_context(relevant_chunks)
        
        # Add user message to history
        self.conversation.add_message("user", user_message)
        
        # Build enhanced prompt with knowledge context
        if knowledge_context:
            enhanced_message = f"{user_message}\n\n{knowledge_context}"
        else:
            enhanced_message = user_message
        
        # Get OpenAI chat completion
        try:
            messages = self.conversation.get_openai_messages()
            # Replace the last user message with the enhanced version
            if messages and messages[-1]["role"] == "user":
                messages[-1]["content"] = enhanced_message
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            assistant_response = response.choices[0].message.content
            
            # Extract source citations
            sources = []
            if relevant_chunks:
                for chunk in relevant_chunks:
                    doc_title = chunk.document.title if chunk.document else "Unknown"
                    page_info = f" (Page {chunk.page})" if chunk.page else ""
                    sources.append(f"{doc_title}{page_info}")
            
            # Add assistant response to history
            self.conversation.add_message("assistant", assistant_response, sources)
            
            return assistant_response
            
        except Exception as e:
            error_msg = f"Sorry, I encountered an error: {str(e)}"
            self.conversation.add_message("assistant", error_msg)
            return error_msg
    
    def reset_conversation(self):
        """Reset the conversation history"""
        self.conversation.clear()
        self._setup_system_prompt()
    
    def get_conversation_summary(self) -> str:
        """Get a summary of the current conversation"""
        if not self.conversation.messages:
            return "No conversation history."
        
        message_count = len([m for m in self.conversation.messages if m.role != "system"])
        return f"Conversation with {message_count} messages. Started: {self.conversation.messages[1].timestamp if len(self.conversation.messages) > 1 else 'N/A'}"
@@ .. @@
    async handleChatSubmit(e) {
        e.preventDefault();
        
        const input = document.getElementById('chatInput');
        const question = input.value.trim();
        
        if (!question) return;
        
        // Add user message to chat
        this.addMessage(question, 'user');
        
        // Clear input and show loading
        input.value = '';
        this.showLoading(true);
        
        try {
+            // Add timeout and better error handling
            const response = await fetch(`${this.apiBase}/run_graph`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.authToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user: this.currentUser?.username || 'User',
                    question: question
-                })
+                }),
+                signal: AbortSignal.timeout(30000)  // 30 second timeout
            });
            
            if (response.ok) {
                const result = await response.json();
                
+                // Enhanced response handling
+                const responseText = result.response || result.final_response || 'No response received';
+                const agentUsed = result.agent || result.agents_involved?.[0] || 'AI Assistant';
+                const processingTime = result.processing_time || 0;
+                const aiUsed = result.ai_used || false;
+                
                // Add AI response to chat
-                this.addMessage(result.response, 'assistant', {
-                    agent: result.agent,
+                this.addMessage(responseText, 'assistant', {
+                    agent: agentUsed,
                    edges: result.edges_traversed,
-                    timestamp: result.timestamp
+                    timestamp: result.timestamp,
+                    processing_time: processingTime,
+                    ai_used: aiUsed
                });
                
                // Reload user data to update stats
                await this.loadUserStats();
                await this.loadQueryHistory();
                
            } else {
                const error = await response.json();
-                this.addMessage(`Sorry, there was an error: ${error.detail}`, 'error');
        let messageHTML = `<div class="message-content">${this.formatMessageContent(content)}</div>`;
            }
        } catch (error) {
            const aiIndicator = metadata.ai_used ? '🧠 AI-Powered' : '🤖 Fallback';
            const processingTime = metadata.processing_time ? `${metadata.processing_time.toFixed(2)}s` : '';
            
            console.error('Chat error:', error);
-            this.addMessage('Sorry, there was a network error. Please try again.', 'error');
                    <span class="agent"><i class="fas fa-robot"></i> ${metadata.agent} (${aiIndicator})</span>
+                this.addMessage('Request timed out. Please try a shorter question or check your connection.', 'error');
                    ${metadata.timestamp ? `<span class="time">${new Date(metadata.timestamp).toLocaleTimeString()}</span>` : ''}
                    ${processingTime ? `<span class="processing-time">⏱️ ${processingTime}</span>` : ''}
+                this.addMessage('Sorry, there was a network error. Please try again.', 'error');
+            }
        }
        
        this.showLoading(false);
    }
    
    formatMessageContent(content) {
        """Format message content with proper HTML rendering"""
        if (!content) return '';
        
        // Check if content is JSON
        try {
            const parsed = JSON.parse(content);
            return `<pre class="json-response">${JSON.stringify(parsed, null, 2)}</pre>`;
        } catch {
            // Not JSON, format as regular text with enhanced formatting
            return content
                .replace(/\n/g, '<br>')
                statusSpan.innerHTML = '<i class="fas fa-circle" style="color: green;"></i> Ollama: Connected ✅';
                statusSpan.className = 'status-indicator connected';
                .replace(/\*(.*?)\*/g, '<em>$1</em>')              // Italic
                statusSpan.innerHTML = '<i class="fas fa-circle" style="color: orange;"></i> Ollama: Using Fallbacks ⚡';
                statusSpan.className = 'status-indicator warning';
                .replace(/^- (.+)/gm, '<li>$1</li>')              // List items
                .replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>')        // Wrap lists
            const statusSpan = document.getElementById('ollamaStatus');
            statusSpan.innerHTML = '<i class="fas fa-circle" style="color: red;"></i> Ollama: Error ❌';
            statusSpan.className = 'status-indicator error';
        }
        
        // Check again in 30 seconds
        setTimeout(() => this.checkOllamaStatus(), 30000);
    }
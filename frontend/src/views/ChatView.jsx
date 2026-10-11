import React, { useState, useEffect, useRef } from 'react';
import {
  Bot,
  Send,
  Sparkles,
  RefreshCw,
  User,
  ShieldCheck,
  Stethoscope,
  Users,
  Building2,
  FileText,
  AlertTriangle,
  CheckCircle2,
  Image as ImageIcon,
  Activity,
  Layers,
  ChevronDown,
  Info,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';

const ROLE_PRESETS = {
  PATIENT: {
    title: 'Meet Lumi • Your Health Guide',
    badge: 'PATIENT MODE',
    color: '#10b981',
    description:
      'Clear, friendly answers about your health, symptoms, medications, and upcoming visits.',
    starters: [
      'What are normal healthy ranges for blood pressure?',
      'What are common signs of pneumonia to watch for?',
      'How should I prepare for my upcoming doctor visit?',
      'When should a high fever prompt urgent medical care?',
    ],
  },
  DOCTOR: {
    title: 'Lumi • Clinical Colleague',
    badge: 'CLINICAL MODE',
    color: '#3b82f6',
    description:
      'Fast differential diagnoses, reference lookups, and chest radiograph scan reviews.',
    starters: [
      '🔬 Review sample chest X-ray',
      'Differential diagnosis for acute dyspnea with elevated CRP',
      'Recommended antibiotic regimen for community-acquired pneumonia',
      'Clinical significance of elevated procalcitonin',
    ],
  },
  NURSE: {
    title: 'Lumi • Care & Triage Assistant',
    badge: 'TRIAGE MODE',
    color: '#a855f7',
    description:
      'Immediate bedside escalation criteria, vital sign alerts, and care checklists.',
    starters: [
      'Escalation criteria for SpO2 below 90%',
      'Triage guidelines for chest discomfort in outpatient queue',
      'Post-operative vitals monitoring frequency',
      'Bedside sepsis screening thresholds',
    ],
  },
  ADMIN: {
    title: 'Lumi • Operations Advisor',
    badge: 'OPERATIONS MODE',
    color: '#06b6d4',
    description:
      'Practical strategies for clinic wait times, appointment attendance, and scheduling.',
    starters: [
      'How can our clinic reduce appointment no-shows?',
      'Industry standard targets for outpatient wait times',
      'Balancing clinic schedules during peak morning intake',
      'How to optimize room utilization across departments',
    ],
  },
};

export default function ChatView() {
  const { user, role } = useAuth();
  const currentRole = role || 'PATIENT';
  const roleConfig = ROLE_PRESETS[currentRole] || ROLE_PRESETS.PATIENT;

  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [includeSampleXray, setIncludeSampleXray] = useState(false);

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  // Load existing history
  useEffect(() => {
    async function init() {
      try {
        const historyRes = await api.llm.getHistory();
        if (historyRes && historyRes.messages && historyRes.messages.length > 0) {
          const formatted = historyRes.messages.map((m) => ({
            id: m.id,
            role: m.sender_role,
            text: m.message_text,
            cited_sources: m.cited_sources || [],
            tool_executed: m.tool_executed,
            timestamp: new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          }));
          setMessages(formatted);
        }
      } catch (err) {
        console.warn('No active chat history found:', err);
      }
    }
    init();
  }, [role]);

  const handleSendMessage = async (textToSend = inputText, withXray = includeSampleXray) => {
    const text = (textToSend || '').trim();
    if (!text && !withXray) return;

    const userMsg = {
      id: Date.now(),
      role: 'user',
      text: withXray ? `${text || 'Review sample chest X-ray'}` : text,
      hasXray: withXray,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputText('');
    setIncludeSampleXray(false);
    setLoading(true);

    try {
      const payload = {
        message: text || (withXray ? 'Review this chest radiograph and summarize the clinical findings.' : ''),
        image_path: withXray ? 'sample_pneumonia' : null,
      };

      const res = await api.llm.chat(payload);

      const botMsg = {
        id: Date.now() + 1,
        role: 'assistant',
        text: res.response,
        tool_executed: res.tool_executed,
        tool_result: res.tool_result,
        cited_sources: res.cited_sources || [],
        confidence: res.confidence || 0.95,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, botMsg]);
    } catch (err) {
      console.error('Chat error:', err);
      const errorMsg = {
        id: Date.now() + 1,
        role: 'assistant',
        text: `I had a temporary connection issue. Please make sure the service is running and try again.`,
        isError: true,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleClearChat = async () => {
    if (confirm('Start a fresh conversation with Lumi?')) {
      try {
        await api.llm.clearHistory();
      } catch (err) {
        console.warn('Clear session error:', err);
      }
      setMessages([]);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="page-container chat-page-container">
      {/* Top Banner: Persona Context */}
      <div className="chat-top-banner">
        <div className="chat-banner-info">
          <div className="role-tag-badge" style={{ borderColor: roleConfig.color, color: roleConfig.color }}>
            <span className="pulse-indicator" style={{ background: roleConfig.color }}></span>
            {roleConfig.badge}
          </div>
          <div>
            <h2 className="chat-banner-title">{roleConfig.title}</h2>
            <p className="chat-banner-desc">{roleConfig.description}</p>
          </div>
        </div>

        {/* Status Pill & Clear Button */}
        <div className="chat-banner-actions">
          <div className="engine-specs-pill">
            <div className="spec-dot green"></div>
            <span className="spec-label">Lumi is Ready</span>
          </div>

          <button className="clear-chat-btn" onClick={handleClearChat} title="Start New Conversation">
            <RefreshCw size={14} />
            <span>New Chat</span>
          </button>
        </div>
      </div>

      {/* Main Chat Flow Container */}
      <div className="chat-body-card">
        {/* Messages Feed */}
        <div className="chat-messages-scroll">
          {messages.length === 0 ? (
            <div className="chat-welcome-state">
              <div className="welcome-avatar-box" style={{ background: `${roleConfig.color}20`, borderColor: roleConfig.color }}>
                <Bot size={36} color={roleConfig.color} />
              </div>
              <h3>Hi {user?.first_name || 'there'}! I'm Lumi 👋</h3>
              <p>
                How can I help you today? Ask me any question below or choose a suggested topic to get started immediately.
              </p>

              {/* Starter Prompt Chips */}
              <div className="starters-grid">
                <div className="starters-header">
                  <Sparkles size={14} color="#60a5fa" />
                  <span>Suggested for you:</span>
                </div>
                {roleConfig.starters.map((starter, idx) => (
                  <button
                    key={idx}
                    className="starter-chip"
                    onClick={() => {
                      if (starter.includes('Review sample chest X-ray')) {
                        handleSendMessage('Please review this sample chest X-ray scan and provide findings.', true);
                      } else {
                        handleSendMessage(starter, false);
                      }
                    }}
                  >
                    <span>{starter}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="messages-list">
              {messages.map((msg) => (
                <div key={msg.id} className={`chat-message-row ${msg.role}`}>
                  <div className="message-avatar">
                    {msg.role === 'user' ? (
                      <User size={18} color="#ffffff" />
                    ) : (
                      <Bot size={18} color={roleConfig.color} />
                    )}
                  </div>

                  <div className="message-content-wrapper">
                    <div className="message-meta">
                      <span className="sender-name">
                        {msg.role === 'user'
                          ? `${user?.first_name || 'You'}`
                          : `Lumi`}
                      </span>
                      <span className="message-time">{msg.timestamp}</span>
                    </div>

                    <div className="message-bubble">
                      {msg.hasXray && (
                        <div className="attached-xray-badge">
                          <ImageIcon size={14} color="#60a5fa" />
                          <span>Attached: Chest Radiograph</span>
                        </div>
                      )}

                      {/* Render text with basic markdown/bullet formatting */}
                      <div className="message-text">
                        {msg.text.split('\n').map((line, lIdx) => {
                          if (line.startsWith('### ')) {
                            return <h4 key={lIdx} className="bubble-h3">{line.replace('### ', '')}</h4>;
                          }
                          if (line.startsWith('**') && line.endsWith('**')) {
                            return <p key={lIdx} className="bubble-bold">{line.replace(/\*\*/g, '')}</p>;
                          }
                          if (line.startsWith('- ') || line.startsWith('* ')) {
                            return (
                              <li key={lIdx} className="bubble-bullet">
                                {line.replace(/^[-*]\s+/, '')}
                              </li>
                            );
                          }
                          if (!line.trim()) {
                            return <div key={lIdx} style={{ height: '8px' }} />;
                          }
                          return <p key={lIdx}>{line}</p>;
                        })}
                      </div>

                      {/* Radiograph Scan Output Card */}
                      {msg.tool_result && (
                        <div className="tool-result-card">
                          <div className="tool-result-header">
                            <div className="tool-title-group">
                              <Activity size={16} color="#3b82f6" />
                              <span className="tool-title">Radiograph Scan Review</span>
                            </div>
                            <span
                              className={`acuity-pill ${
                                msg.tool_result.acuity_level === 'URGENT_TRIAGE' ? 'urgent' : 'routine'
                              }`}
                            >
                              {msg.tool_result.acuity_level === 'URGENT_TRIAGE' ? 'URGENT' : 'ROUTINE'}
                            </span>
                          </div>

                          <div className="tool-result-body">
                            {msg.tool_result.gradcam_heatmap_base64 && (
                              <div className="tool-image-container">
                                <img
                                  src={`data:image/png;base64,${msg.tool_result.gradcam_heatmap_base64}`}
                                  alt="Pulmonary Heatmap"
                                  className="gradcam-heatmap-img"
                                />
                                <div className="heatmap-caption">
                                  <span>Infiltration Heatmap</span>
                                </div>
                              </div>
                            )}

                            <div className="tool-details-grid">
                              <div className="tool-stat-box">
                                <span className="stat-label">Finding</span>
                                <span className="stat-val classification">
                                  {msg.tool_result.predicted_class}
                                </span>
                              </div>
                              <div className="tool-stat-box">
                                <span className="stat-label">Certainty</span>
                                <span className="stat-val">
                                  {typeof msg.tool_result.confidence === 'number'
                                    ? `${(msg.tool_result.confidence * 100).toFixed(1)}%`
                                    : '95.0%'}
                                </span>
                              </div>
                              <div className="tool-stat-box full-width">
                                <span className="stat-label">Clinical Summary</span>
                                <p className="stat-desc">{msg.tool_result.clinical_findings}</p>
                              </div>
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Reference Sources Card */}
                      {msg.cited_sources && msg.cited_sources.length > 0 && (
                        <div className="citations-tray">
                          <div className="citations-header">
                            <FileText size={12} color="#94a3b8" />
                            <span>Reference Sources:</span>
                          </div>
                          <div className="citations-tags">
                            {msg.cited_sources.map((src, sIdx) => (
                              <span key={sIdx} className="citation-tag">
                                {src.source || 'Medical Knowledge Base'} {src.topic ? `• ${src.topic}` : ''}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}

              {/* Thinking Indicator */}
              {loading && (
                <div className="chat-message-row assistant thinking-row">
                  <div className="message-avatar">
                    <Bot size={18} color={roleConfig.color} />
                  </div>
                  <div className="message-content-wrapper">
                    <div className="message-meta">
                      <span className="sender-name">Lumi</span>
                      <span className="thinking-status">Thinking...</span>
                    </div>
                    <div className="thinking-bubble">
                      <div className="pulsing-dot"></div>
                      <div className="pulsing-dot"></div>
                      <div className="pulsing-dot"></div>
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginLeft: 8 }}>
                        Lumi is preparing your response...
                      </span>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Chat Input Console */}
        <div className="chat-input-bar">
          {includeSampleXray && (
            <div className="xray-attachment-banner">
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Activity size={16} color="#60a5fa" />
                <span style={{ fontSize: '0.82rem', color: '#93c5fd' }}>
                  Chest radiograph attached for review
                </span>
              </div>
              <button
                className="cancel-attachment-btn"
                onClick={() => setIncludeSampleXray(false)}
              >
                ✕ Cancel
              </button>
            </div>
          )}

          <div className="chat-input-inner">
            {/* Doctor-specific tool quick trigger */}
            {currentRole === 'DOCTOR' && (
              <button
                className={`tool-trigger-btn ${includeSampleXray ? 'active' : ''}`}
                onClick={() => setIncludeSampleXray((prev) => !prev)}
                title="Attach sample chest radiograph to review"
              >
                <Activity size={16} />
                <span>Review Sample X-Ray</span>
              </button>
            )}

            <textarea
              className="chat-textarea"
              placeholder={
                currentRole === 'DOCTOR'
                  ? 'Ask a clinical question or review a scan...'
                  : currentRole === 'PATIENT'
                  ? 'Ask a health question in plain English...'
                  : currentRole === 'NURSE'
                  ? 'Ask about triage protocols or vitals criteria...'
                  : 'Ask about clinic operations or scheduling...'
              }
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
              rows={1}
            />

            <button
              className="chat-send-btn"
              disabled={loading || (!inputText.trim() && !includeSampleXray)}
              onClick={() => handleSendMessage()}
            >
              {loading ? (
                <div className="spinner-sm" />
              ) : (
                <>
                  <span>Send</span>
                  <Send size={15} />
                </>
              )}
            </button>
          </div>

          <div className="chat-input-footer">
            <span className="privacy-note">
              🔒 Confidential & Secure Healthcare Assistant • Clinical Decision Support
            </span>
            <span className="shortcut-hint">Press [Enter] to send, [Shift+Enter] for new line</span>
          </div>
        </div>
      </div>
    </div>
  );
}

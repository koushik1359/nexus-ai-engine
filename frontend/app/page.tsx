"use client";

import { useState, useRef, useEffect } from "react";
import {
    Send, Bot, User, Database, Loader2, Sparkles,
    ChevronDown, ChevronUp, PanelLeftOpen, PanelLeftClose,
    Table2, Key, Link2, Download, History, Trash2, X, Upload
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, PieChart, Pie, Cell, Legend
} from "recharts";

import { Message } from "../src/types";
import { CHART_COLORS, extractChartData } from "../src/lib/utils";
import { Collapsible } from "../src/components/ui/Collapsible";
import { ChatGPTLeftSidebar } from "../src/components/layout/ChatGPTLeftSidebar";

// ============================================================
// MAIN PAGE
// ============================================================
const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://nexus-api-backend-atckcaggb2ahhzgf.centralus-01.azurewebsites.net";

export default function Home() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [currentSteps, setCurrentSteps] = useState<string[]>([]);
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [historyOpen, setHistoryOpen] = useState(false);
    const [uploadStatus, setUploadStatus] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const [sessionId, setSessionId] = useState<string>("");

    useEffect(() => {
        // Create a unique session ID for isolating uploaded files
        setSessionId(`sess_${Math.random().toString(36).substring(2, 11)}`);
    }, []);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, currentSteps]);

    // Load history from localStorage
    useEffect(() => {
        const saved = localStorage.getItem("nexus_history");
        if (saved) {
            try { setMessages(JSON.parse(saved)); } catch { }
        }
    }, []);

    // Save history
    useEffect(() => {
        if (messages.length > 0) {
            localStorage.setItem("nexus_history", JSON.stringify(messages));
        }
    }, [messages]);

    const clearHistory = () => {
        setMessages([]);
        localStorage.removeItem("nexus_history");
    };

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setUploadStatus(`Uploading ${file.name}...`);

        const formData = new FormData();
        formData.append("file", file);

        try {
            const res = await fetch(`${API_URL}/upload`, {
                method: "POST",
                headers: { "X-Session-ID": sessionId },
                body: formData,
            });
            const data = await res.json();

            if (data.error) {
                setUploadStatus(`❌ ${data.error}`);
            } else {
                setUploadStatus(`✅ ${data.message}`);
                // Add a system message to the chat
                setMessages((prev) => [
                    ...prev,
                    {
                        role: "assistant",
                        content: `📁 **File uploaded!** Table \`${data.table_name}\` created with ${data.row_count} rows and ${data.columns?.length || 0} columns. You can now ask questions about this data!`,
                    },
                ]);
            }
        } catch {
            setUploadStatus("❌ Upload failed. Is the backend running?");
        }

        // Clear upload status after 4 seconds
        setTimeout(() => setUploadStatus(null), 4000);
        // Reset file input
        if (fileInputRef.current) fileInputRef.current.value = "";
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || isLoading) return;

        const userMessage = input.trim();
        setInput("");
        setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
        setIsLoading(true);
        setCurrentSteps([]);

        try {
            const response = await fetch(`${API_URL}/query/stream`, {
                method: "POST",
                headers: { 
                    "Content-Type": "application/json",
                    "X-Session-ID": sessionId
                },
                body: JSON.stringify({ query: userMessage }),
            });

            const reader = response.body?.getReader();
            const decoder = new TextDecoder();
            let finalAnswer = "";
            let sqlQuery = "";
            let chartParsed: { data: any[], type: "bar" | "pie" } | null = null;
            const steps: string[] = [];

            if (reader) {
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value);
                    const lines = chunk.split("\n").filter((line) => line.startsWith("data: "));

                    for (const line of lines) {
                        const jsonStr = line.replace("data: ", "");
                        try {
                            const data = JSON.parse(jsonStr);
                            if (data.type === "step") {
                                steps.push(data.content);
                                setCurrentSteps([...steps]);
                            } else if (data.type === "sql") {
                                sqlQuery = data.content;
                            } else if (data.type === "answer") {
                                finalAnswer = data.content;
                            } else if (data.type === "chart") {
                                const cData = data.content;
                                chartParsed = {
                                    data: cData,
                                    type: cData.length <= 6 ? "pie" : "bar"
                                };
                            }
                        } catch { }
                    }
                }
            }

            setMessages((prev) => [
                ...prev,
                {
                    role: "assistant",
                    content: finalAnswer,
                    sql: sqlQuery,
                    steps,
                    chartData: chartParsed?.data,
                    chartType: chartParsed?.type,
                },
            ]);
            setCurrentSteps([]);
        } catch (err) {
            console.error("Fetch error:", err);
            setMessages((prev) => [
                ...prev,
                { role: "assistant", content: "Connection error. Is the backend service online?" },
            ]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex h-screen bg-[#212121] text-gray-200 font-sans selection:bg-violet-500/30">
            {/* Left Sidebar */}
            <ChatGPTLeftSidebar sessionId={sessionId} isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} onNewChat={clearHistory} />

            {/* Main Chat Area */}
            <div className="flex-1 flex flex-col min-w-0 h-full relative">
                {/* ── HEADER ── */}
                <header className="absolute top-0 w-full z-10 flex items-center justify-between p-3 pointer-events-none">
                    <div className="flex items-center pointer-events-auto gap-1">
                        {!sidebarOpen && (
                            <button
                                onClick={() => setSidebarOpen(true)}
                                className="p-2 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
                                title="Open sidebar"
                            >
                                <PanelLeftOpen className="w-5 h-5" />
                            </button>
                        )}
                        <button className="px-3 py-1.5 rounded-xl hover:bg-white/5 text-gray-200 text-[15px] font-medium transition-colors flex items-center gap-2">
                            Nexus AI <span className="text-gray-500 font-normal">GPT-4o</span> <ChevronDown className="w-4 h-4 text-gray-500" />
                        </button>
                    </div>

                    <div className="flex items-center gap-2 pointer-events-auto pr-2">
                        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20">
                            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                            <span className="text-[11px] text-emerald-400 font-medium tracking-wide">Live Database</span>
                        </div>
                    </div>
                </header>

                {/* Upload Status Toast */}
                {uploadStatus && (
                    <div className="absolute top-16 left-1/2 -translate-x-1/2 z-50 px-4 py-2.5 rounded-full bg-white text-[#212121] font-medium shadow-xl text-sm animate-pulse flex items-center gap-2">
                        {uploadStatus.includes("✅") ? "✅" : "⏳"} {uploadStatus.replace("✅ ", "").replace("❌ ", "")}
                    </div>
                )}

                {/* ── MESSAGES ── */}
                <main className="flex-1 overflow-y-auto">
                    <div className="max-w-3xl mx-auto px-5 py-8 space-y-6">
                        {/* Empty state — Welcome Screen */}
                        {messages.length === 0 && (
                            <div className="flex flex-col items-center justify-center min-h-[50vh]">
                                <div className="w-16 h-16 rounded-full bg-white flex items-center justify-center mb-6 shadow-xl shadow-white/5">
                                    <Sparkles className="w-8 h-8 text-black" />
                                </div>
                                <h2 className="text-3xl font-semibold text-white mb-8 tracking-tight">
                                    What can I help with?
                                </h2>
                                
                                {/* Suggested Questions */}
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-2xl px-4">
                                    {[
                                        "Top 5 venues by ticket revenue?",
                                        "Genre with highest fan satisfaction?",
                                        "Merchandise items below restock threshold",
                                        "Compare VIP vs General sales by venue",
                                    ].map((q) => (
                                        <button
                                            key={q}
                                            onClick={() => {
                                                setInput(q);
                                                setTimeout(() => {
                                                    const form = document.querySelector("form");
                                                    if (form) form.requestSubmit();
                                                }, 50);
                                            }}
                                            className="text-left px-5 py-3.5 text-sm text-gray-300 hover:bg-[#2f2f2f] border border-[#2f2f2f] rounded-2xl transition-colors duration-200"
                                        >
                                            <p className="font-medium">{q}</p>
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Messages */}
                        {messages.map((msg, i) => (
                            <div key={i}>
                                {msg.role === "user" ? (
                                    <div className="flex justify-end pt-4 pb-2">
                                        <div className="max-w-[70%] bg-[#2f2f2f] text-white px-5 py-3.5 rounded-3xl rounded-tr-lg text-sm leading-relaxed whitespace-pre-wrap">
                                            {msg.content}
                                        </div>
                                    </div>
                                ) : (
                                    <div className="flex gap-4 pt-4 pb-6">
                                        <div className="shrink-0 w-8 h-8 rounded-full bg-white flex items-center justify-center mt-0.5 shadow-sm">
                                            <Sparkles className="w-5 h-5 text-black" />
                                        </div>
                                        <div className="flex-1 min-w-0 space-y-3">
                                            {/* Agent Steps (Collapsible) */}
                                            {msg.steps && msg.steps.length > 0 && (
                                                <Collapsible title="Agent Reasoning" icon={<Sparkles className="w-3 h-3" />}>
                                                    <div className="space-y-1 pt-2">
                                                        {msg.steps.map((step: string, j: number) => (
                                                            <p key={j} className={`text-xs font-mono leading-relaxed ${step.includes('❌') ? 'text-red-400' : 'text-gray-400'}`}>
                                                                {step}
                                                            </p>
                                                        ))}

                                                    </div>
                                                </Collapsible>
                                            )}

                                            {/* SQL Query (Collapsible) */}
                                            {msg.sql && (
                                                <Collapsible title="SQL Query" icon={<Database className="w-3 h-3" />}>
                                                    <pre className="text-xs text-emerald-400 font-mono whitespace-pre-wrap leading-relaxed pt-2">
                                                        {msg.sql}
                                                    </pre>
                                                </Collapsible>
                                            )}

                                            {/* ── CHART ── */}
                                            {msg.chartData && msg.chartData.length > 0 && (
                                                <div className="rounded-xl border border-white/[0.08] bg-[#12121e] p-4">
                                                    <p className="text-xs font-medium text-gray-400 mb-3">📊 Auto-Generated Visualization</p>
                                                    <ResponsiveContainer width="100%" height={260}>
                                                        {msg.chartType === "pie" ? (
                                                            <PieChart>
                                                                <Pie
                                                                    data={msg.chartData}
                                                                    cx="50%" cy="50%"
                                                                    innerRadius={50} outerRadius={90}
                                                                    dataKey={Object.keys(msg.chartData[0]).find((k) => k !== "name") || ""}
                                                                    nameKey="name"
                                                                    label={({ name, value }) => `${name}: ${typeof value === 'number' ? value.toLocaleString() : value}`}
                                                                    labelLine={false}
                                                                >
                                                                    {msg.chartData.map((_: any, idx: number) => (
                                                                        <Cell key={idx} fill={CHART_COLORS[idx % CHART_COLORS.length]} />
                                                                    ))}
                                                                </Pie>
                                                                <Tooltip
                                                                    contentStyle={{ background: "#1a1a2e", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", color: "#fff", fontSize: "12px" }}
                                                                />
                                                                <Legend wrapperStyle={{ fontSize: "11px", color: "#9ca3af" }} />
                                                            </PieChart>
                                                        ) : (
                                                            <BarChart data={msg.chartData}>
                                                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                                                                <XAxis dataKey="name" tick={{ fill: "#9ca3af", fontSize: 11 }} angle={-20} textAnchor="end" height={60} />
                                                                <YAxis tick={{ fill: "#9ca3af", fontSize: 11 }} />
                                                                <Tooltip
                                                                    contentStyle={{ background: "#1a1a2e", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", color: "#fff", fontSize: "12px" }}
                                                                />
                                                                {Object.keys(msg.chartData[0])
                                                                    .filter((k) => k !== "name")
                                                                    .map((key: string, idx: number) => (
                                                                        <Bar key={key} dataKey={key} fill={CHART_COLORS[idx % CHART_COLORS.length]} radius={[4, 4, 0, 0]} />
                                                                    ))}
                                                            </BarChart>
                                                        )}
                                                    </ResponsiveContainer>
                                                </div>
                                            )}

                                            {/* ── THE ANSWER ── */}
                                            <div className="pr-12 text-[#ececec]">
                                                <div className="text-[15px] leading-relaxed markdown-prose">
                                                    <ReactMarkdown
                                                        components={{
                                                            p: ({ children }) => <p className="mb-4">{children}</p>,
                                                            strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
                                                            li: ({ children }) => <li className="mb-1">{children}</li>,
                                                            ul: ({ children }) => <ul className="pl-5 mb-4 list-disc">{children}</ul>,
                                                            ol: ({ children }) => <ol className="pl-5 mb-4 list-decimal">{children}</ol>,
                                                            h1: ({ children }) => <h1 className="text-xl font-bold text-white mb-3 mt-6">{children}</h1>,
                                                            h2: ({ children }) => <h2 className="text-lg font-bold text-white mb-3 mt-6">{children}</h2>,
                                                            h3: ({ children }) => <h3 className="text-md font-bold text-white mb-2 mt-4">{children}</h3>,
                                                            code: ({ children }) => <code className="bg-[#2f2f2f] text-white px-1.5 py-0.5 rounded text-[13px] font-mono">{children}</code>,
                                                        }}
                                                    >{msg.content}</ReactMarkdown>
                                                </div>
                                            </div>

                                            {/* Export CSV button */}
                                            {msg.sql && (
                                                <button
                                                    onClick={async () => {
                                                        const prevMsg = messages[i - 1];
                                                        if (!prevMsg) return;
                                                        const resp = await fetch(`${API_URL}/export`, {
                                                            method: "POST",
                                                            headers: { 
                                                                "Content-Type": "application/json",
                                                                "X-Session-ID": sessionId
                                                            },
                                                            body: JSON.stringify({ query: prevMsg.content }),
                                                        });
                                                        const blob = await resp.blob();
                                                        const url = URL.createObjectURL(blob);
                                                        const a = document.createElement("a");
                                                        a.href = url;
                                                        a.download = "nexus_export.csv";
                                                        a.click();
                                                    }}
                                                    className="inline-flex items-center gap-1.5 text-xs text-gray-400 hover:text-violet-400 transition-colors px-3 py-1.5 rounded-lg hover:bg-white/[0.03] border border-transparent hover:border-white/[0.06]"
                                                >
                                                    <Download className="w-3 h-3" /> Export as CSV
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                )}
                            </div>
                        ))}

                        {/* Loading indicator */}
                        {isLoading && (
                            <div className="flex gap-3">
                                <div className="shrink-0 w-8 h-8 rounded-lg bg-gradient-to-br from-violet-600 to-indigo-500 flex items-center justify-center mt-1">
                                    <Loader2 className="w-4 h-4 text-white animate-spin" />
                                </div>
                                <div className="flex-1">
                                    <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4 space-y-1.5">
                                        <p className="text-xs font-medium text-violet-400 mb-2">Agent Working...</p>
                                        {currentSteps.map((step: string, j: number) => (
                                            <p key={j} className={`text-xs font-mono ${step.includes('❌') ? 'text-red-400 pulse-animation' : 'text-gray-400'}`}>
                                                {step}
                                            </p>
                                        ))}

                                        {currentSteps.length === 0 && (
                                            <div className="flex items-center gap-2">
                                                <div className="w-2 h-2 rounded-full bg-violet-500 animate-pulse" />
                                                <span className="text-xs text-gray-500">Initializing agents...</span>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        )}

                        <div ref={messagesEndRef} />
                    </div>
                </main>

                {/* ── INPUT BAR ── */}
                <div className="shrink-0 bg-[#212121] px-5 pb-6 pt-2">
                    <form onSubmit={handleSubmit} className="max-w-3xl mx-auto relative">
                        {/* Hidden file input */}
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept=".csv,.sql"
                            onChange={handleFileUpload}
                            className="hidden"
                        />
                        
                        <div className="flex items-end gap-2 bg-[#2f2f2f] rounded-[26px] px-3 py-3 shadow-sm border border-transparent focus-within:border-white/10 transition-colors">
                            {/* Upload Button */}
                            <button
                                type="button"
                                onClick={() => fileInputRef.current?.click()}
                                className="p-2.5 rounded-full hover:bg-white/10 text-gray-400 hover:text-white transition-colors flex-shrink-0 mb-0.5"
                                title="Attach a file"
                            >
                                <Upload className="w-5 h-5" />
                            </button>
                            
                            <textarea
                                value={input}
                                onChange={(e) => {
                                    setInput(e.target.value);
                                    e.target.style.height = 'auto';
                                    e.target.style.height = `${Math.min(e.target.scrollHeight, 200)}px`;
                                }}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' && !e.shiftKey) {
                                        e.preventDefault();
                                        const form = e.currentTarget.closest('form');
                                        if (form) form.requestSubmit();
                                    }
                                }}
                                placeholder="Message Nexus AI..."
                                className="flex-1 bg-transparent text-white placeholder-gray-400 outline-none text-[15px] resize-none min-h-[44px] max-h-[200px] py-3 overflow-y-auto leading-relaxed"
                                disabled={isLoading}
                                rows={1}
                            />
                            
                            <button
                                type="submit"
                                disabled={isLoading || !input.trim()}
                                className={`p-2 rounded-full flex-shrink-0 mb-0.5 transition-colors ${
                                    input.trim() && !isLoading 
                                        ? "bg-white text-black hover:bg-gray-200" 
                                        : "bg-[#212121] text-gray-500 cursor-not-allowed"
                                }`}
                            >
                                {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4 ml-0.5" />}
                            </button>
                        </div>
                        <p className="text-[11px] text-gray-500 mt-3 text-center">
                            Nexus AI can make mistakes. Check important info.
                        </p>
                    </form>
                </div>
            </div>
        </div>
    );
}

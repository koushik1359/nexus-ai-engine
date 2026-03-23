"use client";

import { useState, useEffect } from "react";
import { Sparkles, PanelLeftClose, Database, Loader2, Table2, Key, Link2 } from "lucide-react";
import { TableSchema } from "../../types";

export function ChatGPTLeftSidebar({ sessionId, isOpen, onClose, onNewChat }: { sessionId: string; isOpen: boolean; onClose: () => void; onNewChat: () => void }) {
    const [schema, setSchema] = useState<Record<string, TableSchema>>({});
    const [loading, setLoading] = useState(true);
    const [expandedTable, setExpandedTable] = useState<string | null>(null);

    useEffect(() => {
        if (isOpen) {
            const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://nexus-api-backend-atckcaggb2ahhzgf.centralus-01.azurewebsites.net";
            fetch(`${API_URL}/schema`, {
                headers: { "X-Session-ID": sessionId }
            })
                .then((res) => res.json())
                .then((data) => { setSchema(data.schema); setLoading(false); })
                .catch(() => setLoading(false));
        }
    }, [isOpen]);

    if (!isOpen) return null;

    return (
        <div className="w-[260px] shrink-0 border-r border-[#2f2f2f] bg-[#171717] flex flex-col h-full overflow-hidden">
            {/* New Chat & Close Buttons */}
            <div className="p-3 flex items-center justify-between">
                <button
                    onClick={onNewChat}
                    className="flex items-center gap-2.5 flex-1 hover:bg-white/[0.08] p-2 rounded-lg transition-colors text-sm text-gray-200"
                >
                    <div className="shrink-0 w-7 h-7 rounded-full bg-white flex items-center justify-center">
                        <Sparkles className="w-4 h-4 text-black" />
                    </div>
                    <span className="font-medium">New chat</span>
                </button>
                <button onClick={onClose} className="p-2 ml-2 hover:bg-white/[0.08] rounded-lg text-gray-400 hover:text-white transition-colors">
                    <PanelLeftClose className="w-5 h-5" />
                </button>
            </div>

            <div className="px-4 pb-2 pt-4">
                <p className="text-xs font-semibold text-gray-500 mb-3 tracking-wider flex items-center gap-2">
                    <Database className="w-3.5 h-3.5" />
                    DATA EXPLORER
                </p>
            </div>

            <div className="flex-1 overflow-y-auto px-3 pb-3 space-y-1">
                {loading ? (
                    <div className="flex items-center justify-center py-10">
                        <Loader2 className="w-5 h-5 text-gray-500 animate-spin" />
                    </div>
                ) : (
                    Object.entries(schema).map(([tableName, table]) => (
                        <div key={tableName} className="rounded-lg overflow-hidden">
                            <button
                                onClick={() => setExpandedTable(expandedTable === tableName ? null : tableName)}
                                className="w-full flex items-center gap-2 px-3 py-2 hover:bg-white/[0.05] rounded-lg transition-colors"
                            >
                                <Table2 className="w-3.5 h-3.5 text-gray-400" />
                                <span className="text-sm font-medium text-gray-200">{tableName}</span>
                                <span className="ml-auto text-[10px] text-gray-500 bg-[#212121] px-1.5 py-0.5 rounded-full border border-white/[0.08]">
                                    {table.row_count}
                                </span>
                            </button>

                            {expandedTable === tableName && (
                                <div className="px-8 py-2 space-y-1.5 border-l-2 border-white/[0.04] ml-4 mt-1 mb-2">
                                    {table.columns.map((col: {name: string; type: string; nullable: boolean}) => (
                                        <div key={col.name} className="flex items-center justify-between gap-2 py-0.5">
                                            <div className="flex items-center gap-1.5 min-w-0">
                                                {table.primary_keys.includes(col.name) ? (
                                                    <Key className="w-3 h-3 text-amber-500 shrink-0" />
                                                ) : table.foreign_keys.some((fk: {column: string[]; references: string}) => fk.column.includes(col.name)) ? (
                                                    <Link2 className="w-3 h-3 text-blue-500 shrink-0" />
                                                ) : null}
                                                <span className="text-xs text-gray-400 truncate">{col.name}</span>
                                            </div>
                                            <span className="text-[10px] text-gray-600 font-mono shrink-0">{col.type.toLowerCase()}</span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}

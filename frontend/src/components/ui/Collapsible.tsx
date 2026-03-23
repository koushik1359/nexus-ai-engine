"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";

export function Collapsible({ title, icon, children, defaultOpen = false }: {
    title: string;
    icon: React.ReactNode;
    children: React.ReactNode;
    defaultOpen?: boolean;
}) {
    const [isOpen, setIsOpen] = useState(defaultOpen);
    return (
        <div className="rounded-xl border border-white/[0.06] overflow-hidden bg-[#12121e]">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full flex items-center gap-2 px-4 py-2.5 text-xs font-medium text-gray-400 hover:text-gray-300 hover:bg-white/[0.02] transition-colors"
            >
                {icon}
                {title}
                <span className="ml-auto">
                    {isOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </span>
            </button>
            {isOpen && <div className="px-4 pb-3 border-t border-white/[0.04]">{children}</div>}
        </div>
    );
}

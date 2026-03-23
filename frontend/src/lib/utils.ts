export const CHART_COLORS = ["#8b5cf6", "#6366f1", "#3b82f6", "#06b6d4", "#10b981", "#f59e0b", "#ef4444", "#ec4899"];

export function extractChartData(sqlResult: string): { data: any[]; type: "bar" | "pie" } | null {
    try {
        const parsed = JSON.parse(sqlResult);
        if (!Array.isArray(parsed) || parsed.length === 0 || parsed.length > 20) return null;

        const keys = Object.keys(parsed[0]);

        // Filter out ID columns — they're numeric but meaningless for charts
        const ignoredPatterns = ["_id", "id"];
        const isIgnored = (k: string) =>
            ignoredPatterns.some((p) => k.toLowerCase() === p || k.toLowerCase().endsWith(p));

        const numericKeys = keys.filter((k) =>
            !isIgnored(k) &&
            parsed.every((row: any) => typeof row[k] === "number" || !isNaN(parseFloat(row[k])))
        );

        // Prioritize meaningful metric columns
        const priorityPatterns = ["revenue", "total", "count", "sales", "price", "amount", "sum", "avg", "quantity"];
        const sortedNumericKeys = [...numericKeys].sort((a, b) => {
            const aPriority = priorityPatterns.findIndex((p) => a.toLowerCase().includes(p));
            const bPriority = priorityPatterns.findIndex((p) => b.toLowerCase().includes(p));
            if (aPriority !== -1 && bPriority === -1) return -1;
            if (aPriority === -1 && bPriority !== -1) return 1;
            return 0;
        });

        // Use first non-numeric key as label, or fallback to "name" key
        const labelKey = keys.find((k) => !numericKeys.includes(k) && !isIgnored(k)) || keys.find((k) => !numericKeys.includes(k));

        if (!labelKey || sortedNumericKeys.length === 0) return null;

        // Use at most 2 metrics for cleaner charts
        const metricsToChart = sortedNumericKeys.slice(0, 2);

        const data = parsed.map((row: any) => {
            const item: any = { name: String(row[labelKey]).substring(0, 25) };
            metricsToChart.forEach((k) => {
                item[k] = parseFloat(row[k]);
            });
            return item;
        });

        return { data, type: parsed.length <= 6 ? "pie" : "bar" };
    } catch {
        return null;
    }
}

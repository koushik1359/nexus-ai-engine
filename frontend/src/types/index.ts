export interface Message {
    role: "user" | "assistant";
    content: string;
    sql?: string;
    steps?: string[];
    chartData?: any[];
    chartType?: "bar" | "pie";
}

export interface TableSchema {
    columns: { name: string; type: string; nullable: boolean }[];
    primary_keys: string[];
    foreign_keys: { column: string[]; references: string }[];
    row_count: number;
}

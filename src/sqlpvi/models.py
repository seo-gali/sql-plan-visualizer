"""Parser-independent analysis and report contracts."""

from dataclasses import dataclass, field


@dataclass
class SourceRange:
    start: int
    end: int
    line: int
    column: int


@dataclass
class AstNode:
    id: str
    kind: str
    label: str
    source: SourceRange | None
    children: list["AstNode"] = field(default_factory=list)


@dataclass
class Reference:
    id: str
    kind: str
    name: str
    qualifier: str
    alias: str
    scope: str
    status: str
    source: SourceRange | None
    candidates: list[str] = field(default_factory=list)
    basis: str = "STATIC"
    relation: str | None = None


@dataclass
class SqlFlowNode:
    id: str
    operation: str
    detail: str
    inputs: list[str]
    source: SourceRange | None = None
    basis: str = "STATIC"


@dataclass
class SqlFlow:
    nodes: list[SqlFlowNode]
    root: str


@dataclass
class PlanNode:
    id: str
    operation: str
    relation: str | None
    access_method: str | None
    estimated_rows: float | None
    estimated_cost: float | None
    children: list["PlanNode"]
    details: dict
    actual_rows: float | None = None
    actual_loops: float | None = None
    actual_time_ms: float | None = None
    buffers: dict = field(default_factory=dict)


@dataclass
class ExecutionPlan:
    vendor: str
    mode: str
    root: PlanNode
    basis: str = "DATABASE"
    planning_time_ms: float | None = None
    execution_time_ms: float | None = None


@dataclass
class ColumnMetadata:
    name: str
    data_type: str
    nullable: bool
    null_fraction: float | None
    distinct_estimate: float | None


@dataclass
class RelationMetadata:
    relation: str
    schema: str
    name: str
    estimated_rows: float
    columns: list[ColumnMetadata]
    indexes: dict[str, str]
    basis: str = "DATABASE"


@dataclass
class Evidence:
    id: str
    target_id: str
    observation: str
    basis: str = "DATABASE"


@dataclass
class Recommendation:
    id: str
    title: str
    evidence: list[Evidence]
    reason: str
    conditions: str
    limitations: str
    verification: str
    suggested_sql: str
    basis: str = "RECOMMENDATION"


@dataclass
class Report:
    filename: str
    sql: str
    dialect: str
    status: str
    ast: AstNode
    references: list[Reference]
    flow: SqlFlow
    warnings: list[str] = field(default_factory=list)
    basis: str = "STATIC"
    plan: ExecutionPlan | None = None
    metadata: list[RelationMetadata] = field(default_factory=list)
    recommendations: list[Recommendation] = field(default_factory=list)

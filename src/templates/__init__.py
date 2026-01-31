"""Templates module for ARBuilder.

Provides curated templates for:
- Stylus smart contracts (Rust/WASM)
- Backend applications (NestJS, Express)
- Frontend applications (Next.js, wagmi, RainbowKit)
- Indexer subgraphs (The Graph)
- Oracle integrations (Chainlink)
"""

# Stylus Templates
from .stylus_templates import (
    StylusTemplate,
    COUNTER_TEMPLATE,
    VENDING_MACHINE_TEMPLATE,
    SIMPLE_ERC20_TEMPLATE,
    ACCESS_CONTROL_TEMPLATE,
    TEMPLATES as STYLUS_TEMPLATES,
    select_template as select_stylus_template,
    get_template as get_stylus_template,
    list_templates as list_stylus_templates,
)

# Backend Templates
from .backend_templates import (
    BackendTemplate,
    NESTJS_STYLUS_TEMPLATE,
    EXPRESS_STYLUS_TEMPLATE,
    NESTJS_GRAPHQL_TEMPLATE,
    API_GATEWAY_TEMPLATE,
    BACKEND_TEMPLATES,
    select_backend_template,
    get_backend_template,
    list_backend_templates,
)

# Frontend Templates
from .frontend_templates import (
    FrontendTemplate,
    NEXTJS_WAGMI_TEMPLATE,
    DAISYUI_COMPONENTS_TEMPLATE,
    CONTRACT_DASHBOARD_TEMPLATE,
    TOKEN_INTERFACE_TEMPLATE,
    FRONTEND_TEMPLATES,
    select_frontend_template,
    get_frontend_template,
    list_frontend_templates,
)

# Indexer Templates
from .indexer_templates import (
    IndexerTemplate,
    ERC20_SUBGRAPH_TEMPLATE,
    ERC721_SUBGRAPH_TEMPLATE,
    DEFI_SUBGRAPH_TEMPLATE,
    CUSTOM_EVENTS_SUBGRAPH_TEMPLATE,
    INDEXER_TEMPLATES,
    select_indexer_template,
    get_indexer_template,
    list_indexer_templates,
)

# Oracle Templates
from .oracle_templates import (
    OracleTemplate,
    PRICE_FEED_TEMPLATE,
    VRF_TEMPLATE,
    AUTOMATION_TEMPLATE,
    FUNCTIONS_TEMPLATE,
    ORACLE_TEMPLATES,
    select_oracle_template,
    get_oracle_template,
    list_oracle_templates,
)

# Legacy aliases for backwards compatibility
TEMPLATES = STYLUS_TEMPLATES
select_template = select_stylus_template
get_template = get_stylus_template
list_templates = list_stylus_templates

__all__ = [
    # Stylus
    "StylusTemplate",
    "COUNTER_TEMPLATE",
    "VENDING_MACHINE_TEMPLATE",
    "SIMPLE_ERC20_TEMPLATE",
    "ACCESS_CONTROL_TEMPLATE",
    "STYLUS_TEMPLATES",
    "TEMPLATES",
    "select_stylus_template",
    "select_template",
    "get_stylus_template",
    "get_template",
    "list_stylus_templates",
    "list_templates",
    # Backend
    "BackendTemplate",
    "NESTJS_STYLUS_TEMPLATE",
    "EXPRESS_STYLUS_TEMPLATE",
    "NESTJS_GRAPHQL_TEMPLATE",
    "API_GATEWAY_TEMPLATE",
    "BACKEND_TEMPLATES",
    "select_backend_template",
    "get_backend_template",
    "list_backend_templates",
    # Frontend
    "FrontendTemplate",
    "NEXTJS_WAGMI_TEMPLATE",
    "DAISYUI_COMPONENTS_TEMPLATE",
    "CONTRACT_DASHBOARD_TEMPLATE",
    "TOKEN_INTERFACE_TEMPLATE",
    "FRONTEND_TEMPLATES",
    "select_frontend_template",
    "get_frontend_template",
    "list_frontend_templates",
    # Indexer
    "IndexerTemplate",
    "ERC20_SUBGRAPH_TEMPLATE",
    "ERC721_SUBGRAPH_TEMPLATE",
    "DEFI_SUBGRAPH_TEMPLATE",
    "CUSTOM_EVENTS_SUBGRAPH_TEMPLATE",
    "INDEXER_TEMPLATES",
    "select_indexer_template",
    "get_indexer_template",
    "list_indexer_templates",
    # Oracle
    "OracleTemplate",
    "PRICE_FEED_TEMPLATE",
    "VRF_TEMPLATE",
    "AUTOMATION_TEMPLATE",
    "FUNCTIONS_TEMPLATE",
    "ORACLE_TEMPLATES",
    "select_oracle_template",
    "get_oracle_template",
    "list_oracle_templates",
]

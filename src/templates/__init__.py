"""Templates module for ARBuilder.

Provides curated templates for:
- Stylus smart contracts (Rust/WASM)
- Backend applications (NestJS, Express)
- Frontend applications (Next.js, wagmi, RainbowKit)
- Indexer subgraphs (The Graph)
- Oracle integrations (Chainlink)
- Orbit chain deployment (@arbitrum/orbit-sdk)
"""

# Stylus Templates
# Backend Templates
from .backend_templates import (
    API_GATEWAY_TEMPLATE,
    BACKEND_TEMPLATES,
    EXPRESS_STYLUS_TEMPLATE,
    NESTJS_GRAPHQL_TEMPLATE,
    NESTJS_STYLUS_TEMPLATE,
    BackendTemplate,
    get_backend_template,
    list_backend_templates,
    select_backend_template,
)

# Frontend Templates
from .frontend_templates import (
    CONTRACT_DASHBOARD_TEMPLATE,
    DAISYUI_COMPONENTS_TEMPLATE,
    FRONTEND_TEMPLATES,
    NEXTJS_WAGMI_TEMPLATE,
    TOKEN_INTERFACE_TEMPLATE,
    FrontendTemplate,
    get_frontend_template,
    list_frontend_templates,
    select_frontend_template,
)

# Indexer Templates
from .indexer_templates import (
    CUSTOM_EVENTS_SUBGRAPH_TEMPLATE,
    DEFI_SUBGRAPH_TEMPLATE,
    ERC20_SUBGRAPH_TEMPLATE,
    ERC721_SUBGRAPH_TEMPLATE,
    INDEXER_TEMPLATES,
    IndexerTemplate,
    get_indexer_template,
    list_indexer_templates,
    select_indexer_template,
)

# Oracle Templates
from .oracle_templates import (
    AUTOMATION_TEMPLATE,
    FUNCTIONS_TEMPLATE,
    ORACLE_TEMPLATES,
    PRICE_FEED_TEMPLATE,
    VRF_TEMPLATE,
    OracleTemplate,
    get_oracle_template,
    list_oracle_templates,
    select_oracle_template,
)
from .orbit_templates import (
    ANYTRUST_CONFIG_TEMPLATE as ORBIT_ANYTRUST_CONFIG_TEMPLATE,
)
from .orbit_templates import (
    CHAIN_CONFIG_TEMPLATE as ORBIT_CHAIN_CONFIG_TEMPLATE,
)
from .orbit_templates import (
    CUSTOM_GAS_TOKEN_TEMPLATE as ORBIT_CUSTOM_GAS_TOKEN_TEMPLATE,
)
from .orbit_templates import (
    DEPLOY_ROLLUP_TEMPLATE as ORBIT_DEPLOY_ROLLUP_TEMPLATE,
)
from .orbit_templates import (
    DEPLOY_TOKEN_BRIDGE_TEMPLATE as ORBIT_DEPLOY_TOKEN_BRIDGE_TEMPLATE,
)
from .orbit_templates import (
    GOVERNANCE_TEMPLATE as ORBIT_GOVERNANCE_TEMPLATE,
)
from .orbit_templates import (
    NODE_CONFIG_TEMPLATE as ORBIT_NODE_CONFIG_TEMPLATE,
)

# Orbit Templates
from .orbit_templates import (
    ORBIT_TEMPLATES,
    OrbitTemplate,
    get_orbit_template,
    list_orbit_templates,
    select_orbit_template,
)
from .orbit_templates import (
    ORCHESTRATION_TEMPLATE as ORBIT_ORCHESTRATION_TEMPLATE,
)
from .orbit_templates import (
    VALIDATOR_MANAGEMENT_TEMPLATE as ORBIT_VALIDATOR_MANAGEMENT_TEMPLATE,
)
from .stylus_templates import (
    ACCESS_CONTROL_TEMPLATE,
    COUNTER_TEMPLATE,
    SIMPLE_ERC20_TEMPLATE,
    VENDING_MACHINE_TEMPLATE,
    StylusTemplate,
)
from .stylus_templates import (
    TEMPLATES as STYLUS_TEMPLATES,
)
from .stylus_templates import (
    get_template as get_stylus_template,
)
from .stylus_templates import (
    list_templates as list_stylus_templates,
)
from .stylus_templates import (
    select_template as select_stylus_template,
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
    # Orbit
    "OrbitTemplate",
    "ORBIT_CHAIN_CONFIG_TEMPLATE",
    "ORBIT_DEPLOY_ROLLUP_TEMPLATE",
    "ORBIT_DEPLOY_TOKEN_BRIDGE_TEMPLATE",
    "ORBIT_CUSTOM_GAS_TOKEN_TEMPLATE",
    "ORBIT_VALIDATOR_MANAGEMENT_TEMPLATE",
    "ORBIT_GOVERNANCE_TEMPLATE",
    "ORBIT_NODE_CONFIG_TEMPLATE",
    "ORBIT_ANYTRUST_CONFIG_TEMPLATE",
    "ORBIT_ORCHESTRATION_TEMPLATE",
    "ORBIT_TEMPLATES",
    "select_orbit_template",
    "get_orbit_template",
    "list_orbit_templates",
]

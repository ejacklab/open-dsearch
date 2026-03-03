-- Linus (Sys Arch): Postgres Schema for UHNW Wealth Data
-- One schema per Billionaire, isolated for maximum security.

CREATE TABLE assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_type VARCHAR(50) NOT NULL, -- 'real_estate', 'art', 'yacht', 'equity', 'crypto'
    name TEXT NOT NULL,
    current_valuation NUMERIC(20, 2) NOT NULL,
    currency CHAR(3) DEFAULT 'USD',
    jurisdiction CHAR(2), -- 'MY', 'CH', 'SG', 'US'
    ownership_entity TEXT, -- 'Family Trust A', 'HoldCo Alpha'
    last_appraisal_date TIMESTAMP WITH TIME ZONE,
    tags JSONB -- Custom tags for Passion Assets
);

CREATE TABLE valuation_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID REFERENCES assets(id),
    old_valuation NUMERIC(20, 2),
    new_valuation NUMERIC(20, 2) NOT NULL,
    change_reason TEXT, -- e.g., 'Market fluctuation', 'Manual appraisal'
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID -- Reference to the User/Advisor ID
);

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    action TEXT NOT NULL, -- e.g., 'viewed_asset_detail', 'updated_valuation'
    resource_id UUID,
    metadata JSONB,
    ip_address INET,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE wealth_flows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_asset_id UUID REFERENCES assets(id),
    destination_asset_id UUID REFERENCES assets(id),
    amount NUMERIC(20, 2) NOT NULL,
    flow_type VARCHAR(50) NOT NULL, -- 'dividend', 'transfer', 'sale', 'tax_payment'
    status VARCHAR(20) DEFAULT 'completed',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_asset_valuation ON assets(current_valuation DESC);
CREATE INDEX idx_flow_source ON wealth_flows(source_asset_id);

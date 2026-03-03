-- Liang (DevOps): Seed script for the Billionaire's Son initial portfolio
INSERT INTO assets (asset_type, name, current_valuation, currency, jurisdiction, ownership_entity)
VALUES 
('equity', 'Global Tech HoldCo', 1450000000.00, 'USD', 'SG', 'Family Trust A'),
('real_estate', 'KL Penthouse', 24500000.00, 'USD', 'MY', 'Family Trust A'),
('liquid', 'Swiss Account', 856000000.00, 'USD', 'CH', 'Swiss Trust'),
('yacht', 'Project Obsidian (120m)', 120000000.00, 'USD', 'KY', 'BVI HoldCo Alpha');

-- Audit trail for initial seed
INSERT INTO valuation_history (asset_id, old_valuation, new_valuation, change_reason)
SELECT id, 0.00, current_valuation, 'Initial Seed' FROM assets;

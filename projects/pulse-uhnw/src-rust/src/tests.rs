#[cfg(test)]
mod tests {
    use rust_decimal::Decimal;
    use rust_decimal_macros::dec;
    use crate::{Asset, calculate_net_worth};
    use uuid::Uuid;

    #[test]
    fn test_precision_accumulation() {
        // Sandy (Sr QA): Testing if we can sum 1 million tiny assets without losing a single cent.
        let mut assets = Vec::new();
        let tiny_value = dec!(0.00000001);
        
        for _ in 0..1_000_000 {
            assets.push(Asset {
                id: Uuid::new_v4(),
                asset_type: "micro_equity".to_string(),
                name: "Fractional Share".to_string(),
                current_valuation: tiny_value,
                currency: "USD".to_string(),
            });
        }
        
        let total = calculate_net_worth(assets);
        // 1,000,000 * 0.00000001 should be exactly 0.01
        assert_eq!(total, dec!(0.01));
        println!("✅ Precision Accumulation Test Passed: Exact 0.01 USD maintained.");
    }

    #[test]
    fn test_billionaire_scale_overflow() {
        // Sandy (Sr QA): Testing a portfolio worth $900 Trillion (more than global GDP).
        let assets = vec![
            Asset {
                id: Uuid::new_v4(),
                asset_type: "sovereign_debt".to_string(),
                name: "Country A".to_string(),
                current_valuation: dec!(450_000_000_000_000.00),
                currency: "USD".to_string(),
            },
            Asset {
                id: Uuid::new_v4(),
                asset_type: "sovereign_debt".to_string(),
                name: "Country B".to_string(),
                current_valuation: dec!(450_000_000_000_000.00),
                currency: "USD".to_string(),
            }
        ];
        
        let total = calculate_net_worth(assets);
        assert_eq!(total, dec!(900_000_000_000_000.00));
        println!("✅ Billionaire Scale Test Passed: $900 Trillion handled without overflow.");
    }
}

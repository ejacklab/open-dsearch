import SwiftUI

struct DesignTokens {
    // Obsidian Black
    static let background = Color(red: 0.02, green: 0.02, blue: 0.02)
    // Champagne Gold
    static let accent = Color(red: 0.77, green: 0.70, blue: 0.35)
    // Charcoal Grey for secondary text
    static let secondary = Color(red: 0.20, green: 0.20, blue: 0.20)
    
    // Haptic Presets
    static func hapticFeedback(style: UIImpactFeedbackGenerator.FeedbackStyle) {
        let generator = UIImpactFeedbackGenerator(style: style)
        generator.impactOccurred()
    }
}

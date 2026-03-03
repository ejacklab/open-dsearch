import SwiftUI

struct WealthFlowItem: Identifiable {
    let id = UUID()
    let source: String
    let destination: String
    let amount: Double
    let color: Color
}

struct FlowVisualizerView: View {
    @State private var flows: [WealthFlowItem] = [
        WealthFlowItem(source: "SG HoldCo", destination: "Swiss Trust", amount: 1_200_000, color: .blue),
        WealthFlowItem(source: "Real Estate (KL)", destination: "Family Office", amount: 450_000, color: .green),
        WealthFlowItem(source: "Family Office", destination: "Lifestyle/Expenses", amount: 150_000, color: .orange)
    ]
    
    var body: some View {
        ZStack {
            DesignTokens.background.ignoresSafeArea()
            
            VStack(alignment: .leading, spacing: 30) {
                Text("WEALTH FLOW")
                    .font(.system(size: 16, weight: .light, design: .serif))
                    .foregroundColor(DesignTokens.accent)
                    .tracking(6)
                    .padding(.horizontal)
                
                ScrollView {
                    VStack(spacing: 24) {
                        ForEach(flows) { flow in
                            FlowLinkView(flow: flow)
                        }
                    }
                    .padding()
                }
                
                Spacer()
                
                // Bottom Summary for the Billionaire's Son
                HStack {
                    VStack(alignment: .leading) {
                        Text("Active Velocity")
                            .font(.caption)
                            .foregroundColor(.gray)
                        Text("$1.8M / month")
                            .font(.title3)
                            .foregroundColor(.white)
                    }
                    Spacer()
                    Button(action: { DesignTokens.hapticFeedback(style: .medium) }) {
                        Text("REBALANCE")
                            .font(.system(size: 12, weight: .bold))
                            .foregroundColor(.black)
                            .padding(.horizontal, 20)
                            .padding(.vertical, 10)
                            .background(DesignTokens.accent)
                            .cornerRadius(8)
                    }
                }
                .padding(30)
                .background(DesignTokens.secondary.opacity(0.5))
                .cornerRadius(20, corners: [.topLeft, .topRight])
            }
        }
    }
}

struct FlowLinkView: View {
    let flow: WealthFlowItem
    @State private var animateFlow = false
    
    var body: some View {
        VStack(spacing: 8) {
            HStack {
                Text(flow.source)
                    .font(.system(size: 14, weight: .medium))
                    .foregroundColor(.white)
                Spacer()
                Text(flow.amount, format: .currency(code: "USD"))
                    .font(.system(size: 14, weight: .bold, design: .monospaced))
                    .foregroundColor(DesignTokens.accent)
                Spacer()
                Text(flow.destination)
                    .font(.system(size: 14, weight: .medium))
                    .foregroundColor(.white)
            }
            
            // Animated Sankey-style path (simplified for SwiftUI)
            ZStack(alignment: .leading) {
                Capsule()
                    .fill(DesignTokens.secondary.opacity(0.3))
                    .frame(height: 4)
                
                Capsule()
                    .fill(LinearGradient(colors: [flow.color.opacity(0.1), flow.color, flow.color.opacity(0.1)], startPoint: .leading, endPoint: .trailing))
                    .frame(width: 60, height: 4)
                    .offset(x: animateFlow ? 300 : -60)
            }
            .mask(Capsule())
            .onAppear {
                withAnimation(.linear(duration: 4).repeatForever(autoreverses: false)) {
                    animateFlow = true
                }
            }
        }
        .padding()
        .background(DesignTokens.secondary.opacity(0.2))
        .cornerRadius(12)
    }
}

// Helper to round specific corners
extension View {
    func cornerRadius(_ radius: CGFloat, corners: UIRectCorner) -> some View {
        mask(RoundedCorner(radius: radius, corners: corners))
    }
}

struct RoundedCorner: Shape {
    var radius: CGFloat = .infinity
    var corners: UIRectCorner = .allCorners

    func path(in rect: CGRect) -> Path {
        let path = UIBezierPath(roundedRect: rect, byRoundingCorners: corners, cornerRadii: CGSize(width: radius, height: radius))
        return Path(path.cgPath)
    }
}

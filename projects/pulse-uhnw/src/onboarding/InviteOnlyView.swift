import SwiftUI

struct InviteOnlyView: View {
    @State private var isScanning = false
    @State private var nfcDetected = false
    
    var body: some View {
        ZStack {
            DesignTokens.background.ignoresSafeArea()
            
            VStack(spacing: 40) {
                Spacer()
                
                // The "IYKYK" Logo - Just a black, glowing square
                RoundedRectangle(cornerRadius: 16)
                    .fill(Color.black)
                    .frame(width: 80, height: 80)
                    .shadow(color: DesignTokens.accent.opacity(nfcDetected ? 0.8 : 0.1), radius: 20)
                
                VStack(spacing: 12) {
                    Text("P U L S E")
                        .font(.system(size: 24, weight: .light, design: .serif))
                        .foregroundColor(.white)
                        .tracking(8)
                    
                    Text("Digital Sovereignty.")
                        .font(.system(size: 12, weight: .ultraLight))
                        .foregroundColor(.gray)
                        .tracking(2)
                }
                
                Spacer()
                
                if !nfcDetected {
                    Button(action: { 
                        simulateNFCScan() 
                    }) {
                        HStack(spacing: 12) {
                            Image(systemName: "sensor.tag.radiowaves.forward")
                            Text("TAP TITANIUM CARD TO AUTHENTICATE")
                        }
                        .font(.system(size: 10, weight: .medium, design: .monospaced))
                        .foregroundColor(DesignTokens.accent)
                        .padding(.vertical, 16)
                        .padding(.horizontal, 30)
                        .background(DesignTokens.accent.opacity(0.1))
                        .cornerRadius(30)
                        .overlay(
                            Capsule().stroke(DesignTokens.accent.opacity(0.3), lineWidth: 1)
                        )
                    }
                } else {
                    Text("ENCLAVE UNLOCKED")
                        .font(.system(size: 12, weight: .bold, design: .monospaced))
                        .foregroundColor(.green)
                        .tracking(4)
                        .onAppear {
                            DesignTokens.hapticFeedback(style: .rigid)
                        }
                }
                
                Spacer().frame(height: 40)
            }
        }
    }
    
    // Simulating the hardware interaction
    private func simulateNFCScan() {
        DesignTokens.hapticFeedback(style: .light)
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
            withAnimation(.easeIn(duration: 0.8)) {
                nfcDetected = true
            }
        }
    }
}

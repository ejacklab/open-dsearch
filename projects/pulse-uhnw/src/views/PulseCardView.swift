import SwiftUI
import Combine

class PulseViewModel: ObservableObject {
    @Published var totalNetWorth: Double = 0.0
    @Published var dailyDelta: Double = 0.0
    @Published var deltaPercentage: Double = 0.0
    @Published var lastUpdated: Date = Date()
    @Published var isOffline: Bool = false

    private var cancellables = Set<AnyCancellable>()

    init() {
        // Initial fetch then start polling
        refresh()
        setupPolling()
    }

    func refresh() {
        Task {
            do {
                let worth = try await EnclaveAPI.shared.fetchNetWorth()
                await MainActor.run {
                    self.totalNetWorth = worth
                    self.lastUpdated = Date()
                    self.isOffline = false
                }
            } catch {
                await MainActor.run {
                    self.isOffline = true
                }
            }
        }
    }

    private func setupPolling() {
        Timer.publish(every: 10.0, on: .main, in: .common)
            .autoconnect()
            .sink { [weak self] _ in
                self?.refresh()
            }
            .store(in: &cancellables)
    }
}

struct PulseCardView: View {
    @StateObject private var viewModel = PulseViewModel()
    @State private var isPulsing = false

    var body: some View {
        VStack(alignment: .center, spacing: 12) {
            HStack(spacing: 4) {
                if viewModel.isOffline {
                    Image(systemName: "wifi.slash")
                        .foregroundColor(.red.opacity(0.8))
                        .font(.caption2)
                }
                Text("TOTAL NET WORTH")
                    .font(.system(size: 14, weight: .light, design: .serif))
                    .foregroundColor(viewModel.isOffline ? .gray : DesignTokens.accent.opacity(0.8))
                    .tracking(4)
            }

            Text(viewModel.totalNetWorth, format: .currency(code: "USD"))
                .font(.system(size: 42, weight: .thin, design: .serif))
                .foregroundColor(viewModel.isOffline ? .gray : .white)
                .contentTransition(.numericText()) 
                .shadow(color: DesignTokens.accent.opacity(isPulsing && !viewModel.isOffline ? 0.3 : 0.0), radius: 10)
...
            HStack(spacing: 8) {
                Image(systemName: viewModel.dailyDelta >= 0 ? "arrow.up.right" : "arrow.down.right")
                Text(abs(viewModel.dailyDelta), format: .currency(code: "USD"))
                Text("(\(viewModel.dailyDelta >= 0 ? "+" : "-")\(String(format: "%.2f", viewModel.deltaPercentage))%)")
            }
            .font(.system(size: 14, weight: .medium, design: .monospaced))
            .foregroundColor(viewModel.dailyDelta >= 0 ? Color.green.opacity(0.8) : Color.red.opacity(0.8))
            
            Text("Last verified: \(viewModel.lastUpdated.formatted(date: .omitted, time: .shortened))")
                .font(.system(size: 10, weight: .ultraLight))
                .foregroundColor(.white.opacity(0.4))
                .padding(.top, 8)
        }
        .padding(40)
        .background(DesignTokens.background)
        .cornerRadius(24)
        .overlay(
            RoundedRectangle(cornerRadius: 24)
                .stroke(DesignTokens.accent.opacity(0.1), lineWidth: 1)
        )
        .onAppear {
            withAnimation(.easeInOut(duration: 3).repeatForever(autoreverses: true)) {
                isPulsing = true
            }
        }
        .onTapGesture {
            DesignTokens.hapticFeedback(style: .heavy)
        }
    }
}

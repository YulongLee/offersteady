import Foundation
import AVFoundation
import CoreGraphics
import CoreMedia

#if canImport(ScreenCaptureKit)
import ScreenCaptureKit
#endif

struct RuntimeHealth: Encodable {
    let runtime: String
    let version: String
    let platform: String
    let architecture: String
    let microphonePermission: String
    let screenPermission: String
    let screenCaptureKitAvailable: Bool
    let computerOutputCapturePath: String
    let ready: Bool
    let errors: [String]
}

struct AudioProbeResult: Encodable {
    let runtime: String
    let version: String
    let sourceKind: String
    let permission: String
    let ok: Bool
    let durationMs: Int
    let sampleRate: Double?
    let channelCount: Int?
    let bufferCount: Int
    let frameCount: Int
    let peakRms: Double
    let errorCode: String?
    let message: String
}

struct NativeAudioStreamEvent: Encodable {
    let type: String
    let sourceKind: String
    let sourceId: String
    let capturedAtMs: Int64?
    let durationMs: Int?
    let sampleRateHz: Int?
    let channels: Int?
    let level: Double?
    let audioBase64: String?
    let errorCode: String?
    let message: String?
}

func architectureName() -> String {
    #if arch(arm64)
    return "arm64"
    #elseif arch(x86_64)
    return "x64"
    #else
    return "unknown"
    #endif
}

func microphonePermissionName() -> String {
    switch AVCaptureDevice.authorizationStatus(for: .audio) {
    case .authorized:
        return "granted"
    case .denied:
        return "denied"
    case .restricted:
        return "restricted"
    case .notDetermined:
        return "not-determined"
    @unknown default:
        return "unknown"
    }
}

func screenPermissionName() -> String {
    if CGPreflightScreenCaptureAccess() {
        return "granted"
    }
    return "not-granted"
}

func runtimeHealth() -> RuntimeHealth {
    let microphone = microphonePermissionName()
    let screen = screenPermissionName()

    #if canImport(ScreenCaptureKit)
    let screenCaptureKitAvailable = true
    #else
    let screenCaptureKitAvailable = false
    #endif

    var errors: [String] = []
    if microphone != "granted" {
        errors.append("microphone-permission-required")
    }
    if screen != "granted" {
        errors.append("screen-capture-permission-required")
    }
    if !screenCaptureKitAvailable {
        errors.append("screencapturekit-unavailable")
    }

    return RuntimeHealth(
        runtime: "offersteady-macos-capture-runtime",
        version: "0.1.0",
        platform: "macos",
        architecture: architectureName(),
        microphonePermission: microphone,
        screenPermission: screen,
        screenCaptureKitAvailable: screenCaptureKitAvailable,
        computerOutputCapturePath: screenCaptureKitAvailable ? "ScreenCaptureKit" : "unavailable",
        ready: errors.isEmpty,
        errors: errors
    )
}

func nowMs() -> Int64 {
    return Int64(Date().timeIntervalSince1970 * 1000)
}

func downsampleToPcm16Base64(samples: UnsafePointer<Float>, frameCount: Int, inputSampleRate: Double, targetSampleRate: Double = 16000) -> String {
    if frameCount <= 0 { return "" }
    let ratio = inputSampleRate / targetSampleRate
    let outputLength = max(1, Int(round(Double(frameCount) / ratio)))
    var bytes = [UInt8](repeating: 0, count: outputLength * 2)
    var outputOffset = 0
    for index in 0..<outputLength {
        let start = Int(floor(Double(index) * ratio))
        let end = min(frameCount, Int(floor(Double(index + 1) * ratio)))
        var sum: Float = 0
        var count = 0
        if start < end {
            for sampleIndex in start..<end {
                sum += samples[sampleIndex]
                count += 1
            }
        }
        let averaged = count > 0 ? sum / Float(count) : samples[min(start, frameCount - 1)]
        let normalized = max(-1.0, min(1.0, Double(averaged)))
        let scaled = normalized < 0 ? normalized * 32768.0 : normalized * 32767.0
        let clamped = Int16(max(-32768, min(32767, Int(round(scaled)))))
        bytes[outputOffset] = UInt8(truncatingIfNeeded: clamped)
        bytes[outputOffset + 1] = UInt8(truncatingIfNeeded: clamped >> 8)
        outputOffset += 2
    }
    return Data(bytes).base64EncodedString()
}

func downsampleInterleavedToPcm16Base64(samples: UnsafePointer<Float>, frameCount: Int, channelCount: Int, inputSampleRate: Double, targetSampleRate: Double = 16000) -> String {
    if frameCount <= 0 { return "" }
    let channels = max(1, channelCount)
    let ratio = inputSampleRate / targetSampleRate
    let outputLength = max(1, Int(round(Double(frameCount) / ratio)))
    var bytes = [UInt8](repeating: 0, count: outputLength * 2)
    var outputOffset = 0
    for index in 0..<outputLength {
        let start = Int(floor(Double(index) * ratio))
        let end = min(frameCount, Int(floor(Double(index + 1) * ratio)))
        var sum: Float = 0
        var count = 0
        if start < end {
            for frameIndex in start..<end {
                for channelIndex in 0..<channels {
                    sum += samples[(frameIndex * channels) + channelIndex]
                    count += 1
                }
            }
        }
        let averaged = count > 0 ? sum / Float(count) : samples[min(start, frameCount - 1) * channels]
        let normalized = max(-1.0, min(1.0, Double(averaged)))
        let scaled = normalized < 0 ? normalized * 32768.0 : normalized * 32767.0
        let clamped = Int16(max(-32768, min(32767, Int(round(scaled)))))
        bytes[outputOffset] = UInt8(truncatingIfNeeded: clamped)
        bytes[outputOffset + 1] = UInt8(truncatingIfNeeded: clamped >> 8)
        outputOffset += 2
    }
    return Data(bytes).base64EncodedString()
}

func rmsFor(samples: UnsafePointer<Float>, frameCount: Int) -> Double {
    if frameCount <= 0 { return 0 }
    var sumSquares = 0.0
    for index in 0..<frameCount {
        let value = Double(samples[index])
        sumSquares += value * value
    }
    return sqrt(sumSquares / Double(frameCount))
}

func rmsForInterleaved(samples: UnsafePointer<Float>, frameCount: Int, channelCount: Int) -> Double {
    if frameCount <= 0 { return 0 }
    let channels = max(1, channelCount)
    var sumSquares = 0.0
    var sampleCount = 0
    for frameIndex in 0..<frameCount {
        for channelIndex in 0..<channels {
            let value = Double(samples[(frameIndex * channels) + channelIndex])
            sumSquares += value * value
            sampleCount += 1
        }
    }
    return sampleCount > 0 ? sqrt(sumSquares / Double(sampleCount)) : 0
}

func probeMicrophone(durationMs: Int) -> AudioProbeResult {
    let permission = microphonePermissionName()
    if permission != "granted" {
        return AudioProbeResult(
            runtime: "offersteady-macos-capture-runtime",
            version: "0.1.0",
            sourceKind: "microphone",
            permission: permission,
            ok: false,
            durationMs: durationMs,
            sampleRate: nil,
            channelCount: nil,
            bufferCount: 0,
            frameCount: 0,
            peakRms: 0,
            errorCode: "microphone-permission-required",
            message: "Microphone permission is not granted for this app identity."
        )
    }

    let engine = AVAudioEngine()
    let input = engine.inputNode
    let format = input.outputFormat(forBus: 0)
    var bufferCount = 0
    var frameCount = 0
    var peakRms = 0.0
    let lock = NSLock()

    input.installTap(onBus: 0, bufferSize: 1024, format: format) { buffer, _ in
        let channels = Int(buffer.format.channelCount)
        let frames = Int(buffer.frameLength)
        var sumSquares = 0.0
        var sampleCount = 0
        if let channelData = buffer.floatChannelData {
            for channelIndex in 0..<max(1, channels) {
                let samples = channelData[channelIndex]
                for frameIndex in 0..<frames {
                    let value = Double(samples[frameIndex])
                    sumSquares += value * value
                    sampleCount += 1
                }
            }
        }
        let rms = sampleCount > 0 ? sqrt(sumSquares / Double(sampleCount)) : 0.0
        lock.lock()
        bufferCount += 1
        frameCount += frames
        peakRms = max(peakRms, rms)
        lock.unlock()
    }

    do {
        try engine.start()
        Thread.sleep(forTimeInterval: Double(max(100, durationMs)) / 1000.0)
        engine.stop()
        input.removeTap(onBus: 0)
    } catch {
        input.removeTap(onBus: 0)
        return AudioProbeResult(
            runtime: "offersteady-macos-capture-runtime",
            version: "0.1.0",
            sourceKind: "microphone",
            permission: permission,
            ok: false,
            durationMs: durationMs,
            sampleRate: format.sampleRate,
            channelCount: Int(format.channelCount),
            bufferCount: bufferCount,
            frameCount: frameCount,
            peakRms: peakRms,
            errorCode: "microphone-engine-start-failed",
            message: error.localizedDescription
        )
    }

    lock.lock()
    let resultBufferCount = bufferCount
    let resultFrameCount = frameCount
    let resultPeakRms = peakRms
    lock.unlock()

    return AudioProbeResult(
        runtime: "offersteady-macos-capture-runtime",
        version: "0.1.0",
        sourceKind: "microphone",
        permission: permission,
        ok: resultFrameCount > 0,
        durationMs: durationMs,
        sampleRate: format.sampleRate,
        channelCount: Int(format.channelCount),
        bufferCount: resultBufferCount,
        frameCount: resultFrameCount,
        peakRms: resultPeakRms,
        errorCode: resultFrameCount > 0 ? nil : "microphone-no-frames",
        message: resultFrameCount > 0 ? "Microphone produced PCM frames. Raw audio was not persisted." : "Microphone did not produce PCM frames during the probe."
    )
}

func streamMicrophone(sourceId: String) throws -> Never {
    let permission = microphonePermissionName()
    if permission != "granted" {
        try writeJson(NativeAudioStreamEvent(
            type: "status",
            sourceKind: "microphone",
            sourceId: sourceId,
            capturedAtMs: nil,
            durationMs: nil,
            sampleRateHz: nil,
            channels: nil,
            level: nil,
            audioBase64: nil,
            errorCode: "microphone-permission-required",
            message: "Microphone permission is not granted for this app identity."
        ))
        fflush(stdout)
        exit(65)
    }

    let engine = AVAudioEngine()
    let input = engine.inputNode
    let format = input.outputFormat(forBus: 0)
    let source = sourceId.isEmpty ? "native-microphone" : sourceId
    var lastCapturedAtMs = nowMs()

    input.installTap(onBus: 0, bufferSize: 2048, format: format) { buffer, _ in
        guard let channelData = buffer.floatChannelData else { return }
        let capturedAtMs = nowMs()
        let frameCount = Int(buffer.frameLength)
        if frameCount <= 0 { return }
        let samples = channelData[0]
        let level = rmsFor(samples: samples, frameCount: frameCount)
        let durationMs = max(1, Int(capturedAtMs - lastCapturedAtMs))
        lastCapturedAtMs = capturedAtMs
        let audioBase64 = downsampleToPcm16Base64(samples: samples, frameCount: frameCount, inputSampleRate: format.sampleRate)
        if audioBase64.isEmpty { return }
        try? writeJson(NativeAudioStreamEvent(
            type: "frame",
            sourceKind: "microphone",
            sourceId: source,
            capturedAtMs: capturedAtMs,
            durationMs: durationMs,
            sampleRateHz: 16000,
            channels: 1,
            level: level,
            audioBase64: audioBase64,
            errorCode: nil,
            message: nil
        ))
        fflush(stdout)
    }

    do {
        try engine.start()
        try writeJson(NativeAudioStreamEvent(
            type: "status",
            sourceKind: "microphone",
            sourceId: source,
            capturedAtMs: nil,
            durationMs: nil,
            sampleRateHz: Int(format.sampleRate),
            channels: Int(format.channelCount),
            level: 0,
            audioBase64: nil,
            errorCode: nil,
            message: "Native microphone stream started. Raw audio is only written to stdout for live publishing and is not persisted."
        ))
        fflush(stdout)
        RunLoop.current.run()
        fatalError("Native microphone run loop exited unexpectedly.")
    } catch {
        input.removeTap(onBus: 0)
        try writeJson(NativeAudioStreamEvent(
            type: "status",
            sourceKind: "microphone",
            sourceId: source,
            capturedAtMs: nil,
            durationMs: nil,
            sampleRateHz: Int(format.sampleRate),
            channels: Int(format.channelCount),
            level: 0,
            audioBase64: nil,
            errorCode: "microphone-engine-start-failed",
            message: error.localizedDescription
        ))
        fflush(stdout)
        exit(66)
    }
}

func probeSystemAudio(durationMs: Int) -> AudioProbeResult {
    let screen = screenPermissionName()
    #if canImport(ScreenCaptureKit)
    let available = true
    #else
    let available = false
    #endif
    let errorCode = !available ? "screencapturekit-unavailable" : (screen != "granted" ? "screen-capture-permission-required" : "system-audio-native-probe-pending")
    let message = !available
        ? "ScreenCaptureKit is unavailable on this macOS runtime."
        : (screen != "granted" ? "Screen capture/system audio permission is not granted for this app identity." : "System-output PCM probing is not implemented yet; this result is explicit unsupported evidence, not a successful capture.")
    return AudioProbeResult(
        runtime: "offersteady-macos-capture-runtime",
        version: "0.1.0",
        sourceKind: "system",
        permission: screen,
        ok: false,
        durationMs: durationMs,
        sampleRate: nil,
        channelCount: nil,
        bufferCount: 0,
        frameCount: 0,
        peakRms: 0,
        errorCode: errorCode,
        message: message
    )
}

#if canImport(ScreenCaptureKit)
@available(macOS 12.3, *)
final class SystemAudioStreamOutput: NSObject, SCStreamOutput {
    let sourceId: String
    var lastCapturedAtMs = nowMs()

    init(sourceId: String) {
        self.sourceId = sourceId
    }

    func stream(_ stream: SCStream, didOutputSampleBuffer sampleBuffer: CMSampleBuffer, of outputType: SCStreamOutputType) {
        guard outputType == .audio else { return }
        guard sampleBuffer.isValid else { return }
        let frameCount = CMSampleBufferGetNumSamples(sampleBuffer)
        guard frameCount > 0 else { return }
        guard let formatDescription = CMSampleBufferGetFormatDescription(sampleBuffer),
              let streamDescription = CMAudioFormatDescriptionGetStreamBasicDescription(formatDescription) else { return }
        let sampleRate = streamDescription.pointee.mSampleRate
        let channelCount = max(1, Int(streamDescription.pointee.mChannelsPerFrame))
        let formatFlags = streamDescription.pointee.mFormatFlags
        let isFloat = (formatFlags & kAudioFormatFlagIsFloat) != 0
        let isNonInterleaved = (formatFlags & kAudioFormatFlagIsNonInterleaved) != 0
        guard isFloat else {
            try? writeJson(NativeAudioStreamEvent(
                type: "status",
                sourceKind: "system",
                sourceId: sourceId,
                capturedAtMs: nil,
                durationMs: nil,
                sampleRateHz: Int(sampleRate),
                channels: channelCount,
                level: 0,
                audioBase64: nil,
                errorCode: "system-audio-format-unsupported",
                message: "ScreenCaptureKit returned non-float system audio; conversion is not supported by this runtime."
            ))
            fflush(stdout)
            return
        }

        var audioBufferList = AudioBufferList()
        var blockBuffer: CMBlockBuffer?
        let status = CMSampleBufferGetAudioBufferListWithRetainedBlockBuffer(
            sampleBuffer,
            bufferListSizeNeededOut: nil,
            bufferListOut: &audioBufferList,
            bufferListSize: MemoryLayout<AudioBufferList>.size,
            blockBufferAllocator: nil,
            blockBufferMemoryAllocator: nil,
            flags: kCMSampleBufferFlag_AudioBufferList_Assure16ByteAlignment,
            blockBufferOut: &blockBuffer
        )
        guard status == noErr else { return }
        let capturedAtMs = nowMs()
        let durationMs = max(1, Int(capturedAtMs - lastCapturedAtMs))
        lastCapturedAtMs = capturedAtMs
        let audioBase64: String
        let level: Double
        if isNonInterleaved {
            guard let data = audioBufferList.mBuffers.mData else { return }
            let samples = data.assumingMemoryBound(to: Float.self)
            audioBase64 = downsampleToPcm16Base64(samples: samples, frameCount: frameCount, inputSampleRate: sampleRate)
            level = rmsFor(samples: samples, frameCount: frameCount)
        } else {
            guard let data = audioBufferList.mBuffers.mData else { return }
            let samples = data.assumingMemoryBound(to: Float.self)
            audioBase64 = downsampleInterleavedToPcm16Base64(samples: samples, frameCount: frameCount, channelCount: channelCount, inputSampleRate: sampleRate)
            level = rmsForInterleaved(samples: samples, frameCount: frameCount, channelCount: channelCount)
        }
        if audioBase64.isEmpty { return }
        try? writeJson(NativeAudioStreamEvent(
            type: "frame",
            sourceKind: "system",
            sourceId: sourceId,
            capturedAtMs: capturedAtMs,
            durationMs: durationMs,
            sampleRateHz: 16000,
            channels: 1,
            level: level,
            audioBase64: audioBase64,
            errorCode: nil,
            message: nil
        ))
        fflush(stdout)
    }
}

@available(macOS 12.3, *)
var retainedSystemAudioStream: SCStream?
@available(macOS 12.3, *)
var retainedSystemAudioOutput: SystemAudioStreamOutput?

@available(macOS 12.3, *)
func streamSystemAudioWithScreenCaptureKit(sourceId: String) async throws -> Never {
    let screen = screenPermissionName()
    let source = sourceId.isEmpty ? "native-system-output" : sourceId
    if screen != "granted" {
        try writeJson(NativeAudioStreamEvent(
            type: "status",
            sourceKind: "system",
            sourceId: source,
            capturedAtMs: nil,
            durationMs: nil,
            sampleRateHz: nil,
            channels: nil,
            level: 0,
            audioBase64: nil,
            errorCode: "screen-capture-permission-required",
            message: "Screen capture/system audio permission is not granted for this app identity."
        ))
        fflush(stdout)
        exit(67)
    }
    let content = try await SCShareableContent.excludingDesktopWindows(false, onScreenWindowsOnly: true)
    guard let display = content.displays.first else {
        try writeJson(NativeAudioStreamEvent(
            type: "status",
            sourceKind: "system",
            sourceId: source,
            capturedAtMs: nil,
            durationMs: nil,
            sampleRateHz: nil,
            channels: nil,
            level: 0,
            audioBase64: nil,
            errorCode: "system-audio-display-missing",
            message: "No display is available for ScreenCaptureKit system audio capture."
        ))
        fflush(stdout)
        exit(68)
    }
    let filter = SCContentFilter(display: display, excludingWindows: [])
    let configuration = SCStreamConfiguration()
    configuration.width = 2
    configuration.height = 2
    configuration.minimumFrameInterval = CMTime(value: 1, timescale: 1)
    configuration.capturesAudio = true
    configuration.excludesCurrentProcessAudio = true
    configuration.sampleRate = 16000
    configuration.channelCount = 1
    let output = SystemAudioStreamOutput(sourceId: source)
    let stream = SCStream(filter: filter, configuration: configuration, delegate: nil)
    try stream.addStreamOutput(output, type: .audio, sampleHandlerQueue: DispatchQueue(label: "offersteady.system-audio"))
    retainedSystemAudioOutput = output
    retainedSystemAudioStream = stream
    try await stream.startCapture()
    try writeJson(NativeAudioStreamEvent(
        type: "status",
        sourceKind: "system",
        sourceId: source,
        capturedAtMs: nil,
        durationMs: nil,
        sampleRateHz: 16000,
        channels: 1,
        level: 0,
        audioBase64: nil,
        errorCode: nil,
        message: "Native ScreenCaptureKit system audio stream started. Raw audio is only written to stdout for live publishing and is not persisted."
    ))
    fflush(stdout)
    RunLoop.current.run()
    fatalError("Native system audio run loop exited unexpectedly.")
}
#endif

func streamSystemAudio(sourceId: String) throws -> Never {
    #if canImport(ScreenCaptureKit)
    if #available(macOS 12.3, *) {
        Task {
            do {
                try await streamSystemAudioWithScreenCaptureKit(sourceId: sourceId)
            } catch {
                try? writeJson(NativeAudioStreamEvent(
                    type: "status",
                    sourceKind: "system",
                    sourceId: sourceId.isEmpty ? "native-system-output" : sourceId,
                    capturedAtMs: nil,
                    durationMs: nil,
                    sampleRateHz: nil,
                    channels: nil,
                    level: 0,
                    audioBase64: nil,
                    errorCode: "system-audio-stream-start-failed",
                    message: error.localizedDescription
                ))
                fflush(stdout)
                exit(69)
            }
        }
        RunLoop.current.run()
        fatalError("Native system audio bootstrap run loop exited unexpectedly.")
    }
    #endif
    let result = probeSystemAudio(durationMs: 0)
    try writeJson(NativeAudioStreamEvent(
        type: "status",
        sourceKind: "system",
        sourceId: sourceId.isEmpty ? "native-system-output" : sourceId,
        capturedAtMs: nil,
        durationMs: nil,
        sampleRateHz: nil,
        channels: nil,
        level: 0,
        audioBase64: nil,
        errorCode: result.errorCode,
        message: result.message
    ))
    fflush(stdout)
    exit(result.ok ? 0 : 67)
}

func writeJson<T: Encodable>(_ value: T) throws {
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.sortedKeys]
    let data = try encoder.encode(value)
    FileHandle.standardOutput.write(data)
    FileHandle.standardOutput.write("\n".data(using: .utf8)!)
}

let arguments = CommandLine.arguments.dropFirst()
let command = arguments.first ?? "status"
let firstValue = arguments.dropFirst().first ?? ""
let durationMs = Int(firstValue) ?? 1200

switch command {
case "status":
    try writeJson(runtimeHealth())
case "probe-microphone":
    try writeJson(probeMicrophone(durationMs: durationMs))
case "probe-system":
    try writeJson(probeSystemAudio(durationMs: durationMs))
case "stream-microphone":
    try streamMicrophone(sourceId: firstValue)
case "stream-system":
    try streamSystemAudio(sourceId: firstValue)
default:
    fputs("Unknown command: \(command)\n", stderr)
    exit(64)
}

import CoreGraphics
import Foundation
import ImageIO
import ScreenCaptureKit
import UniformTypeIdentifiers

private enum CaptureError: Error {
    case invalidArguments
    case displayUnavailable
    case applicationUnavailable
    case encodingFailed
}

@main
struct FilteredScreenshot {
    static func main() async {
        do {
            let arguments = CommandLine.arguments
            guard arguments.count == 3,
                  let displayID = CGDirectDisplayID(arguments[1]),
                  let ownerPID = pid_t(arguments[2]) else { throw CaptureError.invalidArguments }

            let content = try await SCShareableContent.excludingDesktopWindows(false, onScreenWindowsOnly: false)
            guard let display = content.displays.first(where: { $0.displayID == displayID }) else {
                throw CaptureError.displayUnavailable
            }
            guard let owner = content.applications.first(where: { $0.processID == ownerPID }),
                  !owner.bundleIdentifier.isEmpty else { throw CaptureError.applicationUnavailable }
            let excluded = content.applications.filter { $0.bundleIdentifier == owner.bundleIdentifier }
            let filter = SCContentFilter(display: display, excludingApplications: excluded, exceptingWindows: [])
            let width = Double(CGDisplayPixelsWide(displayID))
            let height = Double(CGDisplayPixelsHigh(displayID))
            guard width > 0 && height > 0 else { throw CaptureError.displayUnavailable }
            let scale = min(1, 1920 / width, 1080 / height)
            let configuration = SCStreamConfiguration()
            configuration.width = max(1, Int((width * scale).rounded()))
            configuration.height = max(1, Int((height * scale).rounded()))
            configuration.showsCursor = false
            let image = try await SCScreenshotManager.captureImage(contentFilter: filter, configuration: configuration)
            let data = NSMutableData()
            guard let destination = CGImageDestinationCreateWithData(data, UTType.png.identifier as CFString, 1, nil) else {
                throw CaptureError.encodingFailed
            }
            CGImageDestinationAddImage(destination, image, nil)
            guard CGImageDestinationFinalize(destination) else { throw CaptureError.encodingFailed }
            try FileHandle.standardOutput.write(contentsOf: data as Data)
        } catch {
            FileHandle.standardError.write(Data("filtered-screenshot-failed\n".utf8))
            exit(EXIT_FAILURE)
        }
    }
}

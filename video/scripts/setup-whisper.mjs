// Installs whisper.cpp (CPU) and the multilingual "small" model into ./whisper.cpp
import { downloadWhisperModel, installWhisperCpp } from "@remotion/install-whisper-cpp";
import path from "node:path";

const to = path.join(process.cwd(), "whisper.cpp");
await installWhisperCpp({ to, version: "1.5.5" });
await downloadWhisperModel({ model: "small", folder: to });
console.log("whisper.cpp ready in", to);

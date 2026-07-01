import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
Config.setConcurrency(4);
// H.264 MP4 is the safest format for LinkedIn upload.
Config.setCodec("h264");

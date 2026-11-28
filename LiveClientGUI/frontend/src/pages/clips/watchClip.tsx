import { Typography } from "@mui/material";
import { CSSProperties } from "@mui/material/styles";
import { Video, VideoSkin } from "@videojs/react/video";
import { createPlayer, timeFeature, volumeFeature, playbackFeature, 
    controlsFeature, pipFeature, fullscreenFeature } from '@videojs/react'
import { useSearchParams } from "react-router-dom";
import { MediaService } from "../../../bindings/LiveClient";
import React from "react";

const { Player } = createPlayer({
    features: [volumeFeature, timeFeature, playbackFeature, controlsFeature, pipFeature, fullscreenFeature]
});

export function WatchClip() {
    const [searchParams] = useSearchParams();
    const filename = searchParams.get('filename');
    const [src, setSrc] = React.useState<string>("");

    React.useEffect(() => {
        if (filename) {
            MediaService.GetClipURL(filename).then((url) => setSrc(url));
        }
    }, [filename]);

    if (!src) return (
        <>
            <Typography variant="h5" sx={{ fontWeight: 'bold', marginBottom: 2 }}>{filename}</Typography>
            <Typography variant="body1">Loading...</Typography>
        </>
    )

    return (
        <>
            <Typography variant="h5" sx={{ fontWeight: 'bold', marginBottom: 2 }}>{filename}</Typography>
            <Player>
                <VideoSkin style={{ width: '100%', height: '90%', aspectRatio: '16 / 9', '--media-controls-before-start': 'visible' } as CSSProperties}>
                    <Video src={src} playsInline  />
                </VideoSkin>
            </Player>
        </>
    )
}
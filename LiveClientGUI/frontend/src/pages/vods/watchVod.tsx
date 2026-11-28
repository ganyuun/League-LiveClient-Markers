import Typography from '@mui/material/Typography'
import Box from '@mui/material/Box'
import Paper from '@mui/material/Paper'
import Table from '@mui/material/Table'
import TableBody from '@mui/material/TableBody'
import TableCell from '@mui/material/TableCell'
import TableHead from '@mui/material/TableHead'
import TableRow from '@mui/material/TableRow'
import TablePagination from '@mui/material/TablePagination';
import IconButton from '@mui/material/IconButton';
import LaunchIcon from '@mui/icons-material/Launch';
import { CSSProperties } from "@mui/material/styles";
import { Video, VideoSkin } from "@videojs/react/video";
import { Container, createPlayer, timeFeature, volumeFeature, playbackFeature, selectTime,
    usePlayer, controlsFeature, pipFeature, fullscreenFeature, 
    selectPlayback} from '@videojs/react'
import { useSearchParams } from "react-router-dom";
import { MediaService, VodService } from '../../../bindings/LiveClient'
import React from "react";

const { Player } = createPlayer({
    features: [volumeFeature, timeFeature, playbackFeature, controlsFeature, pipFeature, fullscreenFeature]
});

function SeekVod({ seconds }: { seconds: number }) {
    const seeker = usePlayer(selectTime);
    const player = usePlayer(selectPlayback);
    
    const handleSeek = async () => {
        if (!seeker || !player) { return; }
        
        const position = await seeker?.seek(seconds);
        player.play();
        console.log(`Seeked to ${position} successfully!`);
    };

    return (
        <IconButton onClick={handleSeek} disabled={!seeker}>
            <LaunchIcon />
        </IconButton>
    )
}

export function WatchVod() {
    const [searchParams] = useSearchParams();
    const filename = searchParams.get('filename');
    const [src, setSrc] = React.useState<string>("");

    React.useEffect(() => {
        if (filename) { MediaService.GetVodURL(filename).then((url) => setSrc(url)); }
    }, [filename]);

    const [events, setEvents] = React.useState<Array<Record<string, any>>>([]);

    if (filename) {
        React.useEffect(() => {
            VodService.ListEvents(filename).then((events) => { setEvents(events as Array<Record<string, any>>) });
        }, []);
    }

    const [page, setPage] = React.useState(0);
    const [rowsPerPage, setRowsPerPage] = React.useState(5);
    const handleChangePage = (event: unknown, newPage: number) => { setPage(newPage); };
    const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
        setRowsPerPage(+event.target.value);
        setPage(0);
    };
    const emptyRows = page > 0 ? Math.max(0, (1 + page) * rowsPerPage - events.length) : 0;

    if (!src) return (
        <>
            <Typography variant="h5" sx={{ fontWeight: 'bold', marginBottom: 2 }}>{filename}</Typography>
            <Typography variant="body1">Loading...</Typography>
        </>
    )

    function formatTime(seconds: number) {
        const min = Math.floor(seconds / 60).toString()
        const sec = (seconds % 60).toFixed(2).toString()
        return `${min.padStart(2, "0")}:${sec.padStart(5, "0")}`
    }

    if (src && events) return (
        <>
            <Typography variant="h5" sx={{ fontWeight: 'bold', marginBottom: 2 }}>{filename}</Typography>

            <Box sx={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: 3 }}>
                <Player>
                    <VideoSkin style={{ 
                        width: "60%", height: "70%", marginBottom: 6, 
                        '--media-controls-before-start': 'visible', aspectRatio: '16/9',
                        flexGrow: 2 } as CSSProperties}
                    >
                        <Video key={filename} src={src} id="vodPlayer" preload="metadata" playsInline  />
                    </VideoSkin>

                    <Paper sx={{ width: "fit-content", height: "fit-content", flex: "1 | flex-grow || 30%" }} elevation = {2}>
                        <Table sx={{ width: '100%', height: '100%' }} size="small">
                            <TableHead>
                                <TableRow>
                                    <TableCell>Event</TableCell>
                                    <TableCell>Time</TableCell>
                                    <TableCell align="right">Seek</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {events.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                                .map((event) => (
                                    <TableRow key={event.Row} >
                                        <TableCell>{ event.EventName }</TableCell>
                                        <TableCell>{ formatTime(event.EventTime) }</TableCell>
                                        <TableCell align="right"> <SeekVod seconds={event.EventTime} /> </TableCell>
                                    </TableRow>
                                ))}
                                { emptyRows > 0 && ( <TableRow style={{ height: 53 * emptyRows }} /> )}
                            </TableBody>
                        </Table>
                        <TablePagination 
                            component="div"
                            count={events.length}
                            rowsPerPageOptions={[5, 10, 25]}
                            page={page}
                            onPageChange={handleChangePage}
                            rowsPerPage={rowsPerPage}
                            onRowsPerPageChange={handleChangeRowsPerPage}
                            sx={{ width: 'fit-content' }}
                        />
                    </Paper>
                </Player>
            </Box>
        </>
    )

    return (
        <>
            <Typography variant="h5" sx={{ fontWeight: 'bold', marginBottom: 2 }}>{filename}</Typography>

            <Box sx={{ width: '100%', height: '100%', overflow: 'hidden' }}>
                <Player>
                    <VideoSkin style={{ width: '100%', height: '90%', aspectRatio: '16 / 9', '--media-controls-before-start': 'visible', flexGrow: 2 } as CSSProperties}>
                        <Video key={filename} src={src} preload="metadata" playsInline  />
                    </VideoSkin>
                </Player>

                <Typography variant="body1">No events found for this VOD.</Typography>
            </Box>
        </>
    )
}
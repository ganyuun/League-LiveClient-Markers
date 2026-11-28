import Typography from '@mui/material/Typography'
import Box from '@mui/material/Box'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import CardMedia from '@mui/material/CardMedia'
import CardActionArea from '@mui/material/CardActionArea'
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';
import CardActions from '@mui/material/CardActions'
import DeleteIcon from '@mui/icons-material/Delete';
import FolderOpenIcon from '@mui/icons-material/FolderOpen';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import { ClipService, FileService } from "../../../bindings/LiveClient"
import { useNavigate } from "react-router";
import '@videojs/react/video/skin.css';
import React from 'react'

export default function ClipGrid() {
    const [clips, setClips] = React.useState<Array<Record<string, any>>>([]);

    React.useEffect(() => {
        ClipService.ListClips().then((data) => { setClips(data as Array<Record<string, any>>) })
    });

    const [deleteTarget, setTarget] = React.useState<Record<string, null | any>>({ "Open": false, "Folder": null, "Filename": null });
    const handleSetTarget = (open: boolean, folder: null | string, filename: null | string) => { setTarget({ "Open": open, "Folder": folder, "Filename": filename }) }

    const handleDelClip = async (folder: string, filename: string) => {
        await FileService.DeleteFile(folder, filename)
        const data = await ClipService.ListClips()
        setClips(data as Array<Record<string, any>>)
        handleSetTarget(false, folder, filename)
    }

    const navigate = useNavigate();

    function handleNavigate(filename: string) {
        navigate(
            `./watch?filename=${filename}`,
            {
                relative: "route"
            }
        );
    }

    return (
        <>
            <Typography variant="h4" sx={{ fontWeight: 'bold', marginBottom: 2 }}>Clips</Typography>
            <Box sx={{ display: 'flex', gap: 1, flexGrow: 1, flexWrap: 'wrap' }}>
                {clips.map((clip) => (
                    <Card variant='outlined' sx={{ height: 300 }} key={clip.Filename}>
                        <CardActionArea onClick={() => handleNavigate(clip.Filename)}>
                            <CardMedia component='img' image={clip.Thumbnail} height='180' />
                            <CardContent>
                                <Typography variant='h6' sx={{ fontWeight: 'bold' }}>{clip.Filename}</Typography>
                            </CardContent>
                        </CardActionArea>

                        <CardActions>
                            <IconButton onClick={() => handleSetTarget(true, 'clips', clip.Filename)}>
                                <DeleteIcon />
                            </IconButton>
                            <IconButton onClick={() => FileService.RevealFile('clips', clip.Filename)}>
                                <FolderOpenIcon />
                            </IconButton>
                        </CardActions>
                    </Card>
                ))}
            </Box>

            <Dialog open={deleteTarget.Open} onClose={() => handleSetTarget(false, null, null)}>
                <DialogTitle>Delete {deleteTarget.Filename} from {deleteTarget.Folder}?</DialogTitle>
                <DialogContent>
                    <DialogContentText>Deleted clips can't be recovered!</DialogContentText>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => handleDelClip(deleteTarget.Folder, deleteTarget.Filename)}>Yes</Button>
                    <Button onClick={() => handleSetTarget(false, null, null)} autoFocus>No</Button>
                </DialogActions>
            </Dialog>
        </>
    )
}
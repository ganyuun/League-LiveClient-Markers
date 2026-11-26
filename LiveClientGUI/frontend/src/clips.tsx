import Typography from '@mui/material/Typography'
import Box from '@mui/material/Box'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import CardMedia from '@mui/material/CardMedia'
import CardActionArea from '@mui/material/CardActionArea'
// import Dialog from '@mui/material/Dialog';
// import DialogActions from '@mui/material/DialogActions';
// import DialogContent from '@mui/material/DialogContent';
// import DialogContentText from '@mui/material/DialogContentText';
// import DialogTitle from '@mui/material/DialogTitle';
import CardActions from '@mui/material/CardActions'
import DeleteIcon from '@mui/icons-material/Delete';
import { ClipService } from "../bindings/LiveClient"
import React from 'react'
import IconButton from '@mui/material/IconButton';

export default function ClipGrid() {
  const [clips, setClips] = React.useState<Array<Record<string, any>>>([]);

  React.useEffect(() => {
    ClipService.ListClips().then((data) => { setClips(data as Array<Record<string, any>>) })
  });

  return (
    <>
      <Typography variant="h4" sx={{fontWeight: 'bold', marginBottom: 2}}>Clips</Typography>
      <Box sx={{display: 'flex', gap: 1, flexWrap: 'wrap' }}>
        {clips.map((clip) => (
          <Card variant='outlined' sx={{maxWidth: 400, height: 300}}>
            <CardActionArea>
              <CardMedia component='img' image={clip.Thumbnail} height='180' />
              <CardContent>
                <Typography variant='h6' sx={{fontWeight: 'bold'}}>{clip.Filename}</Typography>
              </CardContent>
            </CardActionArea>

            <CardActions>
              <IconButton>
                <DeleteIcon />
              </IconButton>
            </CardActions>
          </Card>
        ))}
      </Box>
    </>
  )
}
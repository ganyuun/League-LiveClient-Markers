import Typography from '@mui/material/Typography'
import Paper from '@mui/material/Paper'
import Table from '@mui/material/Table'
import TableBody from '@mui/material/TableBody'
import TableCell from '@mui/material/TableCell'
import TableContainer from '@mui/material/TableContainer'
import TableHead from '@mui/material/TableHead'
import TableRow from '@mui/material/TableRow'
import TablePagination from '@mui/material/TablePagination';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';
import IconButton from '@mui/material/IconButton';
import StarBorderIcon from '@mui/icons-material/StarBorder';
import StarIcon from '@mui/icons-material/Star';
import DeleteIcon from '@mui/icons-material/Delete';
import React from 'react'
import Button from '@mui/material/Button';
import Avatar from '@mui/material/Avatar';
import { VodService, FileService } from "../../../bindings/LiveClient"
import { Link, useNavigate } from 'react-router-dom'

export default function VodTable() {
  const [vods, setVods] = React.useState<Array<Record<string, any>>>([]);
  const [favs, setFavs] = React.useState<Array<string>>([]);

  React.useEffect(() => {
    VodService.ListVODs().then((data) => { setVods(data as Array<Record<string, any>>) });
  }, [])

  React.useEffect(() => {
    VodService.GetFavorites().then((data) => { setFavs(data as Array<string>) })
  }, []);

  const handleFavorite = async (filename: string) => {
    const newFavs = await VodService.UpdateFavorites(filename)

    if (newFavs) { setFavs(newFavs) }
  }

  const [deleteTarget, setTarget] = React.useState<Record<string, null | any>>({"Open": false, "Folder": null, "Filename": null});
  const handleSetTarget = (open: boolean, folder: null | string, filename: null | string) => { 
    setTarget({ "Open": open, "Folder": folder, "Filename": filename })
  }

  const handleDelVod = async (folder: string, filename: string) => {
    await FileService.DeleteFile(folder, filename)
    const data = await VodService.ListVODs()
    setVods(data as Array<Record<string, any>>)
    handleSetTarget(false, null, null)
  }

  function formatVodCell(value: string) {
    if (!value) return "-";
    else {
      if (value === 'Win') {
        return <Typography variant='body1' sx={{color: 'forestGreen', fontWeight: 'bold'}}>{value}</Typography>
      } else if (value === 'Loss') {
        return <Typography variant='body1' sx={{color: 'crimson', fontWeight: 'bold'}}>{value}</Typography>
      }

      return value;
    }
  }

  function formatImgCell(value: string) {
    if (!value) return "No events data";
    return <Avatar src={value} variant="square" sx={{ width: 35 }} />
  }

  const navigate = useNavigate();

  function handleNavigate(filename: string) {
    navigate(`./watch?filename=${filename}`, {relative: "route"});
  }

  return (
    <>
      <Typography variant="h4" sx={{fontWeight: 'bold', marginBottom: 2}}>Saved VODs</Typography>

      <Paper sx={{ overflow: 'hidden' }} elevation = {2}>
        <TableContainer sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Filename</TableCell>
                <TableCell align="left"></TableCell>
                <TableCell>Champion</TableCell>
                <TableCell>KDA</TableCell>
                <TableCell>Gamemode</TableCell>
                <TableCell>Result</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {vods.map((vod) => (
                <TableRow key={vod.Filename} hover onClick={ () => handleNavigate(vod.Filename) } sx={{ cursor: 'pointer' }}>
                  <TableCell>{ vod.Filename }</TableCell>
                  <TableCell align="left">{ formatImgCell(vod.Icon) }</TableCell>
                  <TableCell>{ formatVodCell(vod.Champion) }</TableCell>
                  <TableCell>{ formatVodCell(vod.KDA) }</TableCell>
                  <TableCell>{ formatVodCell(vod.Gamemode) }</TableCell>
                  <TableCell>{ formatVodCell(vod.Result) }</TableCell>
                  <TableCell align="right">
                    <IconButton aria-label='Favorite button' 
                      onClick={(e) => {e.stopPropagation(); handleFavorite(vod.Filename)}}
                    >
                      { favs.includes(vod.Filename) ? <StarIcon /> : <StarBorderIcon /> }
                    </IconButton>
                    
                    <IconButton aria-label='Delete VOD' 
                      onClick={(e) => {e.stopPropagation(); handleSetTarget(true, 'vods', vod.Filename);}}
                    >
                      <DeleteIcon />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      <Dialog open={deleteTarget.Open} onClose={() => handleSetTarget(false, null, null)}>
        <DialogTitle>Delete {deleteTarget.Filename} from {deleteTarget.Folder}?</DialogTitle>
        <DialogContent>
          <DialogContentText>Deleted VODs and associated events can't be recovered!</DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => handleDelVod(deleteTarget.Folder, deleteTarget.Filename)}>Yes</Button>
          <Button onClick={() => handleSetTarget(false, null, null)} autoFocus>No</Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
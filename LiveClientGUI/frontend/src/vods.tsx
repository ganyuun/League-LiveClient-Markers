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
import StarBorderIcon from '@mui/icons-material/StarBorder';
import StarIcon from '@mui/icons-material/Star';
import DeleteIcon from '@mui/icons-material/Delete';
import React from 'react'
import IconButton from '@mui/material/IconButton';
import Button from '@mui/material/Button';
import Avatar from '@mui/material/Avatar';
import { VodListService, FileService } from "../bindings/LiveClient"

export default function VodTable() {
  const [vods, setVods] = React.useState<Array<Record<string, any>>>([]);
  const [favs, setFavs] = React.useState<Array<string>>([]);

  React.useEffect(() => {
    VodListService.ListVODs().then((data) => { setVods(data as Array<Record<string, any>>) });
  }, [])

  React.useEffect(() => {
    VodListService.GetFavorites().then((data) => { setFavs(data as Array<string>) })
  }, []);

  const handleFavorite = async (filename: string) => {
    const newFavs = await VodListService.UpdateFavorites(filename)

    if (newFavs) { setFavs(newFavs) }
  }

  const [deleteTarget, setTarget] = React.useState<Record<string, null | any>>({"Open": false, "Folder": null, "Filename": null});
  const handleSetTarget = (open: boolean, folder: null | string, filename: null | string) => { 
    setTarget({ "Open": open, "Folder": folder, "Filename": filename })
  }

  const handleDelVod = async (folder: string, filename: string) => {
    await FileService.DeleteFile(folder, filename)
    const data = await VodListService.ListVODs()
    setVods(data as Array<Record<string, any>>)
    handleSetTarget(false, null, null)
  }

  const [page, setPage] = React.useState(0);
  const [rowsPerPage, setRowsPerPage] = React.useState(10);
  const handleChangePage = (event: unknown, newPage: number) => { setPage(newPage); };
  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(+event.target.value);
    setPage(0);
  };

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

  return (
    <>
      <Typography variant="h4" sx={{fontWeight: 'bold', marginBottom: 2}}>Saved VODs</Typography>
      <div>Scientists reveal the Whoa</div>

      <Paper sx={{ overflow: 'hidden' }} elevation = {2}>
        <TableContainer sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          <Table>
            <TableHead>
              <TableCell>Filename</TableCell>
              <TableCell>Icon</TableCell>
              <TableCell>Champion</TableCell>
              <TableCell>KDA</TableCell>
              <TableCell>Gamemode</TableCell>
              <TableCell>Result</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableHead>
            <TableBody>
              {vods.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
              .map((vod) => (
                <TableRow>
                  <TableCell>{ vod.Filename }</TableCell>
                  <TableCell>{ formatImgCell(vod.Icon) }</TableCell>
                  <TableCell>{ formatVodCell(vod.Champion) }</TableCell>
                  <TableCell>{ formatVodCell(vod.KDA) }</TableCell>
                  <TableCell>{ formatVodCell(vod.Gamemode) }</TableCell>
                  <TableCell>{ formatVodCell(vod.Result) }</TableCell>
                  <TableCell align="right">
                    <IconButton aria-label='Favorite button' onClick={() => handleFavorite(vod.Filename)}>
                      { favs.includes(vod.Filename) ? <StarIcon /> : <StarBorderIcon /> }
                    </IconButton>
                    
                    <IconButton aria-label='Delete VOD' onClick={() => handleSetTarget(true, 'vods', vod.Filename)}>
                      <DeleteIcon />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePagination 
              component = "div" 
              count={vods.length}
              page={page}
              onPageChange={handleChangePage}
              rowsPerPage={rowsPerPage}
              onRowsPerPageChange={handleChangeRowsPerPage}
          />
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
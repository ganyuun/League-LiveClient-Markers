import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Typography from '@mui/material/Typography'
import VodTable from './pages/vods/vods'
import ClipGrid from './pages/clips/clips'
import { WatchClip } from './pages/clips/watchClip'
import { WatchVod } from './pages/vods/watchVod'
import { Layout } from './components/layout'
import { Routes, Route } from "react-router";

const darkTheme = createTheme({ palette: { mode: 'dark' }, });

export function App() {
  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <Routes>
        <Route path="/" element={<Layout />} >
          <Route index element={<VodTable />} />
          <Route path="watch" element={ <WatchVod /> } />

          <Route path="clip">
            <Route index element={<ClipGrid />} />
            <Route path="watch" element={ <WatchClip />} />
          </Route>

          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </ThemeProvider>
  )
}

function SettingsPage() {
  return (
    <>
      <Typography variant="h4" sx={{ fontWeight: 'bold', marginBottom: 2 }}>Settings</Typography>
      <div>HI :D</div>
    </>
  )
}

export default App
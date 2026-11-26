import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Typography from '@mui/material/Typography'
import Paper from '@mui/material/Paper'
import Tabs from '@mui/material/Tabs'
import Tab from '@mui/material/Tab'
import Box from '@mui/material/Box'
import VideocamIcon from '@mui/icons-material/Videocam';
import MovieIcon from '@mui/icons-material/Movie';
import SettingsIcon from '@mui/icons-material/Settings';
import VodTable from './vods'
import ClipGrid from './clips'
import React from 'react'

const darkTheme = createTheme({ palette: {mode: 'dark'}, });

export function App() {
  return (
    <>
      <ThemeProvider theme={darkTheme}>
        <CssBaseline>
          <TabLayout />
        </CssBaseline>
      </ThemeProvider>
    </>
  )
}

function TabLayout() {
  const [tab, setTab] = React.useState(0);

  const handleChange = (event: React.SyntheticEvent, newValue: number) => { setTab(newValue); };

  return (
    <>
    <Paper sx={{ flexGrow: 1, display: 'flex', minHeight: '100vh' }}>
      <Tabs
        orientation = "vertical"
        value = {tab}
        onChange = {handleChange}
        sx = {{ borderRight: 1, borderColor: "divider", flexShrink: 0 }}
        centered
      >
        <Tab icon={<VideocamIcon />} label = "VODs" />
        <Tab icon={<MovieIcon />} label = "Clips" />
        <Tab icon={<SettingsIcon />} label = "Settings" />
      </Tabs>

      <Box sx={{flexGrow: 1, mx: 2, my: 2, overflow: 'auto'}}>
        {tab === 0 && <VodTable />}
        {tab === 1 && <ClipGrid />}
        {tab === 2 && <SettingsPage />}
      </Box>
    </Paper>
    </>
  )
}

function SettingsPage() {
  return (
    <>
      <Typography variant="h4" sx={{fontWeight: 'bold', marginBottom: 2}}>Settings</Typography>
      <div>hello</div>
    </>
  )
}

export default App
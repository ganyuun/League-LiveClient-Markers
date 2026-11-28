import { Box, Paper, Tab, Tabs } from "@mui/material"
import { useNavigate, useLocation, Outlet, Link } from "react-router-dom"
import VideocamIcon from '@mui/icons-material/Videocam';
import MovieIcon from '@mui/icons-material/Movie';
import SettingsIcon from '@mui/icons-material/Settings';

export const Layout = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const currentTab = location.pathname.split('/')[1] || '/';

    return (
        <Paper sx={{ flexGrow: 1, display: 'flex', height: '100%', overflow: 'hidden' }}>
            <Tabs
                orientation="vertical"
                value={currentTab}
                onChange={(_, newValue) => navigate(`/${newValue}`)}
                sx={{ borderRight: 1, borderColor: "divider", flexShrink: 0 }}
                centered
            >
                <Tab icon={<Link to="/"><VideocamIcon /></Link>} label="VODs" value="/" />
                <Tab icon={<Link to="/clip"><MovieIcon /></Link>} label="Clips" value="clip" />
                <Tab icon={<Link to="/settings"><SettingsIcon /></Link>} label="Settings" value="settings" />
            </Tabs>

            <Box sx={{ flexGrow: 1, padding: 2, overflow: 'auto' }}>
                <Outlet />
            </Box>
        </Paper>
    )
}
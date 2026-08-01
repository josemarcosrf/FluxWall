import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { Discover } from './pages/Discover';
import { Studio } from './pages/Studio';
import { Library } from './pages/Library';

export default function App(): React.JSX.Element {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Discover />} />
        <Route path="/studio" element={<Studio />} />
        <Route path="/library" element={<Library />} />
        <Route path="*" element={<Discover />} />
      </Routes>
    </BrowserRouter>
  );
}

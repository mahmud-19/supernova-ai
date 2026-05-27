import { useEffect, useState } from 'react';
import { api } from '../api/client';

export function useObjectUrl(path?: string) {
  const [url, setUrl] = useState<string>();
  useEffect(() => {
    if (!path) {
      setUrl(undefined);
      return;
    }
    let alive = true;
    let objectUrl = '';
    api.get(path, { responseType: 'blob' }).then((response) => {
      objectUrl = URL.createObjectURL(response.data);
      if (alive) {
        setUrl(objectUrl);
      }
    });
    return () => {
      alive = false;
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [path]);
  return url;
}

(function (root) {
  'use strict';
  function wheelSpeeds(v, w, separation, radius) {
    if (![v,w,separation,radius].every(Number.isFinite) || separation <= 0 || radius <= 0) {
      throw new RangeError('速度必须是有限数，轮距和轮半径必须大于零');
    }
    return {left:(v-w*separation/2)/radius,right:(v+w*separation/2)/radius};
  }
  function createProgress(storage, ids) {
    const key = 'ros2-control-learning:v1';
    let completed = [];
    let persistent = !!storage;
    try {
      const saved = JSON.parse(storage?.getItem(key) ?? 'null');
      if (saved?.version === 1 && Array.isArray(saved.completed)) {
        completed = [...new Set(saved.completed.filter(id => ids.includes(id)))];
      }
    } catch { persistent = false; }
    function save() {
      try {
        if (!storage) return;
        storage.setItem(key,JSON.stringify({version:1,completed}));
        persistent = true;
      } catch { persistent = false; }
    }
    return {
      get:()=>[...completed],
      has:id=>completed.includes(id),
      complete(id) {
        if (ids.includes(id) && !completed.includes(id)) { completed.push(id); save(); }
        return [...completed];
      },
      reset() { completed = []; save(); return []; },
      isPersistent:()=>persistent
    };
  }
  function resolveLesson(hash, ids) {
    let id;
    try { id = decodeURIComponent(String(hash).replace(/^#/,'')); } catch { id = ''; }
    return ids.includes(id) ? id : 'architecture';
  }
  const api = {wheelSpeeds,createProgress,resolveLesson};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.CourseLogic = api;
})(typeof window !== 'undefined' ? window : globalThis);

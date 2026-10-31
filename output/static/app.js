(function () {
  'use strict';

  /* ---------------- 瀑布流 ---------------- */
  function columnCount() {
    var w = window.innerWidth;
    if (w <= 640) return 2;
    if (w <= 1023) return 3;
    if (w <= 1439) return 4;
    return 5;
  }

  function layoutMasonry(grid) {
    if (!grid._cards) {
      grid._cards = Array.prototype.slice.call(
        grid.querySelectorAll('.card')
      );
    }
    var cards = grid._cards;
    if (!cards.length) return;

    var cols = columnCount();
    grid.classList.add('is-ready');

    var old = grid.querySelectorAll('.masonry-col');
    for (var i = 0; i < old.length; i++) old[i].remove();

    var colEls = [];
    for (var c = 0; c < cols; c++) {
      var el = document.createElement('div');
      el.className = 'masonry-col';
      grid.appendChild(el);
      colEls.push(el);
    }

    cards.forEach(function (card) {
      var target = colEls[0];
      for (var i = 1; i < colEls.length; i++) {
        if (colEls[i].offsetHeight < target.offsetHeight) target = colEls[i];
      }
      target.appendChild(card);
    });
  }

  function initMasonry() {
    var grids = document.querySelectorAll('[data-masonry]');
    grids.forEach(layoutMasonry);

    var timer = null;
    window.addEventListener('resize', function () {
      clearTimeout(timer);
      timer = setTimeout(function () {
        grids.forEach(layoutMasonry);
      }, 150);
    });
  }

  /* ---------------- 轻提示 ---------------- */
  var toastTimer = null;
  function toast(text) {
    var el = document.getElementById('toast');
    if (!el) return;
    el.textContent = text;
    el.hidden = false;
    void el.offsetWidth;
    el.classList.add('is-show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () {
      el.classList.remove('is-show');
      setTimeout(function () { el.hidden = true; }, 240);
    }, 2000);
  }

  /* ---------------- 复制 ---------------- */
  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }
    return new Promise(function (resolve, reject) {
      var area = document.createElement('textarea');
      area.value = text;
      area.setAttribute('readonly', '');
      area.style.position = 'fixed';
      area.style.opacity = '0';
      document.body.appendChild(area);
      area.select();
      var ok = false;
      try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
      document.body.removeChild(area);
      ok ? resolve() : reject(new Error('copy failed'));
    });
  }

  function downloadUrl() {
    var link = document.querySelector('.pan-link a') ||
      document.querySelector('[data-download]');
    return link ? link.getAttribute('href') : '';
  }

  /* ---------------- 搜索 ---------------- */
  function initSearch() {
    var input = document.getElementById('search-input');
    var panel = document.getElementById('search-panel');
    var clearBtn = document.getElementById('search-clear');
    if (!input || !panel) return;

    var items = null;
    var loading = false;
    var results = [];
    var active = -1;
    var timer = null;

    function load() {
      if (items || loading) return;
      loading = true;
      fetch('/search.json')
        .then(function (r) { return r.json(); })
        .then(function (data) {
          items = (data && data.items) || [];
          loading = false;
        })
        .catch(function () {
          items = [];
          loading = false;
        });
    }

    function normalize(text) {
      return (text || '').toLowerCase().replace(/\s+/g, ' ').trim();
    }

    function matches(item, tokens) {
      var code = (item.code || '').toLowerCase();
      return tokens.every(function (t) {
        return item.text.indexOf(t) >= 0 ||
          item.py.indexOf(t) >= 0 ||
          item.ini.indexOf(t) >= 0 ||
          code.indexOf(t) >= 0;
      });
    }

    function buildRow(item) {
      var row = document.createElement('a');
      row.className = 'sr-item';
      row.href = item.url;

      var thumb = document.createElement('div');
      thumb.className = 'sr-thumb';
      if (item.thumb) {
        var img = document.createElement('img');
        img.src = item.thumb;
        img.alt = '';
        img.loading = 'lazy';
        thumb.appendChild(img);
      }

      var body = document.createElement('div');
      body.className = 'sr-body';

      var title = document.createElement('span');
      title.className = 'sr-title';
      title.textContent = item.title;

      var meta = document.createElement('span');
      meta.className = 'sr-meta';
      var code = document.createElement('em');
      code.textContent = item.code;
      meta.appendChild(code);
      meta.appendChild(document.createTextNode(' · ' + item.cat));

      body.appendChild(title);
      body.appendChild(meta);
      row.appendChild(thumb);
      row.appendChild(body);
      return row;
    }

    function render() {
      var query = normalize(input.value);
      clearBtn.hidden = !input.value;

      if (!query) {
        panel.hidden = true;
        panel.innerHTML = '';
        results = [];
        active = -1;
        return;
      }

      if (!items) {
        panel.hidden = false;
        panel.innerHTML = '';
        var loadingRow = document.createElement('div');
        loadingRow.className = 'sr-empty';
        loadingRow.textContent = '搜索中…';
        panel.appendChild(loadingRow);
        return;
      }

      var tokens = query.split(' ');
      results = items.filter(function (it) {
        return matches(it, tokens);
      }).slice(0, 8);
      active = -1;

      panel.innerHTML = '';
      panel.hidden = false;

      if (!results.length) {
        var empty = document.createElement('div');
        empty.className = 'sr-empty';
        empty.textContent = '没有找到相关作品';
        panel.appendChild(empty);
        return;
      }

      results.forEach(function (item) {
        panel.appendChild(buildRow(item));
      });
    }

    function setActive(index) {
      var rows = panel.querySelectorAll('.sr-item');
      if (!rows.length) return;
      active = (index + rows.length) % rows.length;
      for (var i = 0; i < rows.length; i++) {
        rows[i].classList.toggle('is-active', i === active);
      }
      rows[active].scrollIntoView({ block: 'nearest' });
    }

    input.addEventListener('focus', function () {
      load();
      if (input.value) render();
    });

    input.addEventListener('input', function () {
      load();
      clearTimeout(timer);
      timer = setTimeout(render, 150);
    });

    input.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setActive(active + 1);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setActive(active - 1);
      } else if (e.key === 'Enter') {
        var row = panel.querySelectorAll('.sr-item')[active];
        if (row) {
          e.preventDefault();
          window.location.href = row.getAttribute('href');
        }
      } else if (e.key === 'Escape') {
        panel.hidden = true;
        input.blur();
      }
    });

    clearBtn.addEventListener('click', function () {
      input.value = '';
      render();
      input.focus();
    });

    document.addEventListener('click', function (e) {
      if (!e.target.closest || !e.target.closest('.search')) {
        panel.hidden = true;
      }
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') panel.hidden = true;
    });
  }

  /* ---------------- 详情图集 ---------------- */
  function initGallery() {
    var hero = document.getElementById('hero');
    var img = document.getElementById('hero-img');
    if (!hero || !img) return;

    var counter = document.getElementById('hero-index');
    var thumbs = Array.prototype.slice.call(
      document.querySelectorAll('.thumb[data-src]')
    );

    var srcs = thumbs.length
      ? thumbs.map(function (t) { return t.getAttribute('data-src'); })
      : [img.getAttribute('src')];

    var index = 0;

    function show(i) {
      if (!srcs.length) return;
      index = (i + srcs.length) % srcs.length;
      img.src = srcs[index];
      if (counter) counter.textContent = String(index + 1);
      thumbs.forEach(function (t, n) {
        t.classList.toggle('is-active', n === index);
      });
      var activeThumb = thumbs[index];
      if (activeThumb && activeThumb.scrollIntoView) {
        activeThumb.scrollIntoView({ block: 'nearest', inline: 'nearest' });
      }
      [index - 1, index + 1].forEach(function (n) {
        var j = (n + srcs.length) % srcs.length;
        if (j !== index) {
          var pre = new Image();
          pre.src = srcs[j];
        }
      });
    }

    thumbs.forEach(function (t, i) {
      t.addEventListener('click', function () { show(i); });
    });

    var prev = hero.querySelector('.hero-prev');
    var next = hero.querySelector('.hero-next');
    if (prev) prev.addEventListener('click', function () { show(index - 1); });
    if (next) next.addEventListener('click', function () { show(index + 1); });

    document.addEventListener('keydown', function (e) {
      var tag = (e.target.tagName || '').toLowerCase();
      if (tag === 'input' || tag === 'textarea') return;
      if (e.key === 'ArrowLeft') show(index - 1);
      else if (e.key === 'ArrowRight') show(index + 1);
    });

    var startX = null;
    hero.addEventListener('touchstart', function (e) {
      if (!e.touches.length) return;
      startX = e.touches[0].clientX;
    }, { passive: true });
    hero.addEventListener('touchend', function (e) {
      if (startX === null || !e.changedTouches.length) return;
      var dx = e.changedTouches[0].clientX - startX;
      startX = null;
      if (Math.abs(dx) > 46) show(dx > 0 ? index - 1 : index + 1);
    });

    show(0);
  }

  /* ---------------- 复制 / 收藏 / 分享 ---------------- */
  function initActions() {
    document.querySelectorAll('[data-copy]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var url = downloadUrl() || window.location.href;
        copyText(url).then(function () {
          toast('链接已复制');
        }).catch(function () {
          toast('复制失败，请手动复制');
        });
      });
    });

    var favBtn = document.getElementById('fav-btn');
    if (favBtn) {
      var key = 'photo-site:fav:' + favBtn.getAttribute('data-id');
      var on = false;
      try { on = localStorage.getItem(key) === '1'; } catch (e) { on = false; }

      function paint() {
        favBtn.classList.toggle('is-on', on);
        favBtn.setAttribute('aria-pressed', on ? 'true' : 'false');
      }
      paint();

      favBtn.addEventListener('click', function () {
        on = !on;
        try {
          on ? localStorage.setItem(key, '1') : localStorage.removeItem(key);
        } catch (e) { /* 隐私模式下忽略 */ }
        paint();
        toast(on ? '已收藏到当前浏览器' : '已取消收藏');
      });
    }

    var shareBtn = document.getElementById('share-btn');
    if (shareBtn) {
      shareBtn.addEventListener('click', function () {
        var data = {
          title: document.title,
          url: window.location.href
        };
        if (navigator.share) {
          navigator.share(data).catch(function () {});
        } else {
          copyText(data.url).then(function () {
            toast('链接已复制');
          }).catch(function () {
            toast('复制失败，请手动复制');
          });
        }
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      initMasonry();
      initSearch();
      initGallery();
      initActions();
    });
  } else {
    initMasonry();
    initSearch();
    initGallery();
    initActions();
  }
})();

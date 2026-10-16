(function () {
  var box = document.getElementById('lightbox');
  if (!box) return;

  var imgEl = box.querySelector('.lb-img');
  var countEl = box.querySelector('.lb-count');
  var links = Array.prototype.slice.call(document.querySelectorAll('.photo[data-full]'));
  var index = 0;

  function show(i) {
    if (!links.length) return;
    index = (i + links.length) % links.length;
    imgEl.src = links[index].getAttribute('data-full');
    countEl.textContent = (index + 1) + ' / ' + links.length;
    box.hidden = false;
    document.body.style.overflow = 'hidden';
  }

  function hide() {
    box.hidden = true;
    imgEl.removeAttribute('src');
    document.body.style.overflow = '';
  }

  links.forEach(function (a, i) {
    a.addEventListener('click', function (e) {
      e.preventDefault();
      show(i);
    });
  });

  box.querySelector('.lb-close').addEventListener('click', hide);
  box.querySelector('.lb-prev').addEventListener('click', function () { show(index - 1); });
  box.querySelector('.lb-next').addEventListener('click', function () { show(index + 1); });
  box.addEventListener('click', function (e) { if (e.target === box) hide(); });

  document.addEventListener('keydown', function (e) {
    if (box.hidden) return;
    if (e.key === 'Escape') hide();
    else if (e.key === 'ArrowLeft') show(index - 1);
    else if (e.key === 'ArrowRight') show(index + 1);
  });

  var startX = null;
  box.addEventListener('touchstart', function (e) { startX = e.touches[0].clientX; }, { passive: true });
  box.addEventListener('touchend', function (e) {
    if (startX === null) return;
    var dx = e.changedTouches[0].clientX - startX;
    startX = null;
    if (Math.abs(dx) > 40) show(dx > 0 ? index - 1 : index + 1);
  });
})();

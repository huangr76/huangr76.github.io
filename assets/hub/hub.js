'use strict';
const shareDialog = document.querySelector('#share-dialog');
const copyDialog = document.querySelector('#copy-dialog');
const status = document.querySelector('#status');
let statusTimer;

function announce(message) {
  clearTimeout(statusTimer);
  status.textContent = message;
  statusTimer = setTimeout(() => { status.textContent = ''; }, 4000);
}

document.querySelectorAll('[data-share]').forEach(button => {
  if (typeof shareDialog.showModal !== 'function') return;
  button.hidden = false;
  button.addEventListener('click', () => shareDialog.showModal());
});
document.querySelector('#close-dialog').addEventListener('click', () => shareDialog.close());
document.querySelector('#close-copy').addEventListener('click', () => copyDialog.close());
[shareDialog, copyDialog].forEach(dialog => {
  dialog.addEventListener('click', event => {
    if (event.target !== dialog) return;
    const rect = dialog.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
  });
});
document.querySelectorAll('input[readonly]').forEach(input => {
  input.addEventListener('click', () => input.select());
});
document.querySelectorAll('[data-copy]').forEach(button => {
  // The fallback needs native dialogs; ordinary game anchors always work.
  if (typeof copyDialog.showModal !== 'function') return;
  button.hidden = false;
  const original = button.textContent;
  let labelTimer;
  button.addEventListener('click', async () => {
    const url = button.dataset.copy;
    button.disabled = true;
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
      await navigator.clipboard.writeText(url);
      clearTimeout(labelTimer);
      button.textContent = '已复制 ✓';
      announce('链接已复制，可以发给学生。');
      labelTimer = setTimeout(() => { button.textContent = original; }, 2200);
    } catch {
      const input = document.querySelector('#manual-url');
      input.value = url;
      if (!copyDialog.open) copyDialog.showModal();
      input.focus();
      input.select();
    } finally {
      button.disabled = false;
    }
  });
});

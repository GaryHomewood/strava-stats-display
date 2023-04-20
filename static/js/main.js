async function refresh(el) {
  el.classList.add("is-loading");
  fetch('/api/v1/refresh', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      'mode': 'dark'
    })
  }).then(resp => {
    el.classList.remove("is-loading");
  });
}
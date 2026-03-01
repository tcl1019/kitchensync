(function() {
  var items = [];
  var seen = new Set();

  // Find leaf li elements (no child li) that contain "Quantity:"
  // Skip hidden/duplicate lists by checking visibility
  var allLi = document.querySelectorAll('li');
  for (var li of allLi) {
    var text = li.innerText || '';
    if (!text.includes('Quantity:')) continue;
    if (li.querySelectorAll('li').length > 0) continue;
    // Skip items in hidden/off-screen duplicate lists
    if (li.offsetParent === null) continue;

    var lines = text.split('\n').map(function(l) { return l.trim(); }).filter(function(l) { return l; });

    var name = null;
    var qty = 1;

    for (var i = 0; i < lines.length; i++) {
      var line = lines[i];

      // First meaningful line is the product name
      if (!name && line.length > 2 && !/^\$/.test(line) && !/^Quantity/i.test(line) && !/^Current price/i.test(line) && !/^Original price/i.test(line) && !/^Weight /i.test(line) && !/^\d+$/.test(line) && !/each$/i.test(line)) {
        name = line;
      }

      // "Quantity:\n2" or "Quantity: 2" or "Quantity: 2.27 lb"
      if (/^Quantity:/i.test(line)) {
        var im = line.match(/Quantity:\s*(\d+(?:\.\d+)?)/i);
        if (im) {
          qty = Math.round(parseFloat(im[1]));
        } else if (i + 1 < lines.length && /^\d+(?:\.\d+)?/.test(lines[i + 1])) {
          qty = Math.round(parseFloat(lines[i + 1]));
        }
      }
    }

    if (name && !seen.has(name.toLowerCase())) {
      if (qty < 1) qty = 1;
      items.push({ name: name, qty: qty });
      seen.add(name.toLowerCase());
    }
  }

  if (items.length === 0) {
    alert('No items found. Make sure you are on an Instacart order detail page with items expanded.');
    return;
  }

  var formatted = items.map(function(item) {
    return item.name + ' | qty: ' + item.qty;
  }).join('\n');

  navigator.clipboard.writeText(formatted).then(function() {
    alert('Copied ' + items.length + ' items! Paste into PantryPal.');
  }).catch(function() {
    var ta = document.createElement('textarea');
    ta.value = formatted;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    alert('Copied ' + items.length + ' items! Paste into PantryPal.');
  });
})();


var app;
var store = false;
var server = 'http://zolal-files.ap01.aws.af.cm/';
var chrome_app = 'chrome' in window && chrome.app.isInstalled;
var android_app = Boolean(screen.lockOrientation);
var searchResultChars = android_app ? 25 : 50;


// apps
if (chrome_app || android_app)
	store = true;

if (android_app) {
	screen.lockOrientation('portrait');

	// menu button
	document.addEventListener('menubutton', function() { app.address.trigger('menu'); }, false);
	$('[rel=menu]').hide();
}


// app initialization
var initApp = function() {
	$('#views').removeClass('loading');

	app = new AppView();
	app.router = new AddressRouter();
	Backbone.history.start();

	if (Backbone.history.getFragment() == '')
		app.render();

	if (store) {
		$('.store-display').show();
		$('.store-hide').hide();
		$('#download-tafsir').click(download_tafsir);

		if (!localStorage.Quran || localStorage.Quran.split(',').length < 6230)
			download_quran();
	}

	$(window).resize();
	track('Zolal');
}


// window
$(window).resize(function() {
	$('.twitter-typeahead .tt-dropdown-menu').css('max-height', $('#views').height());
});


// settings dialog
$('select#language').val(variables.lang).change(function() {
	$('#pages').html('');
	variables.lang = $(this).val();
	app.position.tafsir.lang = variables.lang;
	app.render();
	show_tafsir_stats();
});


// gestures
$("#views").swipe({
	tap: function(e) {
		if (e.type != 'mouseup') {
			$(e.target).click();

			if (e.target.id == 'page')
				$(e.target).toggleClass('active');
		}
	},
	swipeLeft: function() {
		app.$el.find('.front').find('.glyphicon-chevron-right').click();
	},
	swipeRight: function() {
		app.$el.find('.front').find('.glyphicon-chevron-left').click();
	}
});


// download
var requestUrls = function(urls, index, isStored, storeData, progress) {
	if (index >= urls.length && progress)
		progress(100);

	isStored(urls[index], function() {
			if (progress) progress(100*index/urls.length);
			requestUrls(urls, index+1, isStored, storeData, progress);
		},	function() {
		settings = {
			context: {url: urls[index]},
			url: server + urls[index],
			success: function(data) {
				storeData(this.url, data);
				if (progress) progress(100*index/urls.length);
				requestUrls(urls, index+1, isStored, storeData, progress);
			},
			error : function(xhr, textStatus) {
				setTimeout(function() { $.ajax(this.settings); }, 1000);
				console.log('retry in 1 second ...');
			}
		};
		settings.context.settings = settings;
		$.ajax(settings);
	});
};

var download_quran = function() {
	var storeData = function(url, data) {
		_.each(data.split('\n'), function(item) {
			if (item) {
				item = $.parseJSON(item);
				aya = new Aya(item);
				aya.save();
			}
		});
	}

	var isStored = function(url, success, error) {
		aya = new Aya({id: quran_pages[Number(url.substr(7))][0]});
		aya.fetch({success: success, error: error});
	}

	urls = _.map(quran_pages, function(ayas, page) { return 'quran/p'+ page; });
	requestUrls(urls, 0, isStored, storeData, false);
};

var tafsir_progress = function(percent) {
	if (percent == 100) {
		$('#download-state').hide();
		$('#complete-state').show();
		$('#download-progress').removeClass('active');
	}
	else {
		$('#download-state').show();
		$('#complete-state').hide();
	}

	$('#download-progress .progress-bar').width(Math.round(percent) +'%');
};

var download_tafsir = function() {
	$('#download-tafsir').attr('disabled', 'disabled');
	$('#download-progress').addClass('active');
	track('Almizan Download', {'lang': variables.lang});

	var storeData = function(url, data) {
		bayan = new Bayan({id: url.substr(8), content: data});
		bayan.save();
	}
	var isStored = function(url, success, error) {
		bayan = new Bayan({id: url.substr(8)});
		bayan.fetch({success: success, error: error});
	}

	urls = _.map(almizan_sections, function(section) { return 'almizan_'+ variables.lang +'/'+ section; });
	requestUrls(urls, 0, isStored, storeData, tafsir_progress);
};

var show_tafsir_stats = function() {
	almizan = new Almizan();
	almizan.fetch({
		success: function() {
			sections = almizan.models.filter(function(item) {
				return item.id.substr(0,2) == variables.lang;
			})
			tafsir_progress(100 * sections.length / almizan_sections.length);
		}
	});
}


// main
if (!android_app || localStorage.Quran)
	initApp();
else {
	// read quran.dat before app init
	$.get('quran.dat', function(data) {
		var ids = [];
		data.split('\n').forEach(function(aya) {
			if (!aya) return;
			id = aya.substr(aya.indexOf('id') + 6).slice(0, -2);
			localStorage['Quran-'+ id] = aya;
			ids.push(id);
		});
		localStorage.Quran = ids.join(',');

		initApp();
	});
}

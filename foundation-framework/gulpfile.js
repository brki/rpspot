var gulp = require('gulp'),
    path = require('path'),
    argv = require('yargs').argv,
    gulpif = require('gulp-if'),
    uglify = require('gulp-uglify'),
    del = require('del');

var build_dir = 'build',
    static_dest = '../static/';

var paths = {
  scripts: {
    'js': ['js/*.js'],
    'js/vendor': [
        'bower_components/jquery/dist/jquery.min.js',
        'bower_components/foundation/js/foundation.min.js',
        'bower_components/foundation/js/vendor/modernizr.js',
        'bower_components/foundation/js/vendor/fastclick.js',
        'vendor/jquery-ui-1.11.4.custom/jquery-ui.js',
        'vendor/timepicker/jquery-ui-timepicker-addon.js',
        'vendor/jquery-ui-touch-punch/jquery.ui.touch-punch.min.js'
    ]
  },
  css: {
    'stylesheets': [
        'css_out/app.css',
        'css_out/normalize.css',
        'vendor/jquery-ui-1.11.4.custom/jquery-ui.css'
     ]
  },
  ui_images: {
      'stylesheets/images': [
        'jquery-ui-1.11.4.custom/images/*'
      ]
  }
};

function copy_paths(sources, dest) {
    return result = gulp.src(sources)
        .pipe(gulp.dest(path.join(build_dir, dest)));
}

function get_object_properties(obj) {
    var props = []
    for (var k in obj) {
        if (obj.hasOwnProperty(k)) {
            props.push(k);
        }
    }
    return props;
}

gulp.task('clean', function(cb) {
  // You can use multiple globbing patterns as you would with `gulp.src`
  del(build_dir, cb);
});

gulp.task('collect_app_scripts', ['clean'], function() {
  var dest_path = 'js';
  return result = gulp.src(paths.scripts[dest_path])
    .pipe(gulpif(argv.production, uglify()))
    .pipe(gulp.dest(path.join(build_dir, dest_path)));
});

gulp.task('collect_vendor_scripts', ['clean'], function() {
  var dest_path = 'js/vendor';
  return copy_paths(paths.scripts[dest_path], dest_path);
});

gulp.task('collect_css', ['clean'], function() {
  var dest_path = 'stylesheets';
  return copy_paths(paths.css[dest_path], dest_path);
});

gulp.task('collect_ui_images', ['clean'], function() {
  var dest_path = 'stylesheets/images';
  return copy_paths(paths.ui_images[dest_path], dest_path);
});

gulp.task('provision_static', ['collect_css', 'collect_ui_images', 'collect_app_scripts', 'collect_vendor_scripts'], function() {
  return gulp.src(build_dir + '/**/*')
             .pipe(gulp.dest(static_dest));
});

//// Copy all static images
//gulp.task('images', ['clean'], function() {
//  return gulp.src(paths.images)
//    // Pass in options to the task
//    .pipe(imagemin({optimizationLevel: 5}))
//    .pipe(gulp.dest('build/img'));
//});

// Rerun the task when a file changes
gulp.task('watch', function() {
  // This is probably rather inefficient:
  gulp.watch(paths.scripts['js'].concat(paths.scripts['js/vendor'], paths.css.stylesheets), ['provision_static']);
});

// The default task (called when you run `gulp` from cli)
gulp.task('default', ['provision_static']);

package com.citu.mobilescan;

import android.content.res.Configuration;
import android.graphics.Bitmap;
import android.graphics.Matrix;
import android.media.Image;
import android.opengl.GLES20;
import android.opengl.GLSurfaceView;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.Toast;

import androidx.annotation.RequiresApi;
import androidx.appcompat.app.AppCompatActivity;

import com.citu.mobilescan.helpers.CameraPermissionHelper;
import com.citu.mobilescan.helpers.DisplayRotationHelper;
import com.citu.mobilescan.helpers.FullScreenHelper;
import com.citu.mobilescan.helpers.SnackbarHelper;
import com.citu.mobilescan.helpers.TrackingStateHelper;
import com.citu.mobilescan.rendering.BackgroundRenderer;
import com.citu.mobilescan.rendering.BoxRenderer;
import com.citu.mobilescan.rendering.DepthRenderer;
import com.google.ar.core.ArCoreApk;
import com.google.ar.core.Camera;
import com.google.ar.core.Config;
import com.google.ar.core.Frame;
import com.google.ar.core.Plane;
import com.google.ar.core.Pose;
import com.google.ar.core.Session;
import com.google.ar.core.TrackingState;
import com.google.ar.core.exceptions.CameraNotAvailableException;
import com.google.ar.core.exceptions.UnavailableApkTooOldException;
import com.google.ar.core.exceptions.UnavailableArcoreNotInstalledException;
import com.google.ar.core.exceptions.UnavailableDeviceNotCompatibleException;
import com.google.ar.core.exceptions.UnavailableSdkTooOldException;
import com.google.ar.core.exceptions.UnavailableUserDeclinedInstallationException;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.FloatBuffer;
import java.util.Random;

import javax.microedition.khronos.egl.EGLConfig;
import javax.microedition.khronos.opengles.GL10;

/**
 * This is a simple example that shows how to create an augmented reality (AR) application using the
 * ARCore Raw Depth API. The application will show 3D point-cloud data of the environment.
 */
public class MainActivity extends AppCompatActivity implements GLSurfaceView.Renderer {
    private static final String TAG = MainActivity.class.getSimpleName();

    // Rendering. The Renderers are created here, and initialized when the GL surface is created.
    private GLSurfaceView surfaceView;

    private boolean installRequested;

    private Session session;
    private final SnackbarHelper messageSnackbarHelper = new SnackbarHelper();
    private DisplayRotationHelper displayRotationHelper;

    private final BackgroundRenderer backgroundRenderer = new BackgroundRenderer();
    private final DepthRenderer depthRenderer = new DepthRenderer();
    private final BoxRenderer boxRenderer = new BoxRenderer();

    private boolean capture = false;
    private Random rand = new Random();
    private final String IP = "http://192.168.254.117:8000/modeler/view/";
    private Button captureButton;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        surfaceView = findViewById(R.id.surfaceview);
        captureButton = findViewById(R.id.capture_button);
        displayRotationHelper = new DisplayRotationHelper(/*context=*/ this);

        // Set up renderer.
        surfaceView.setPreserveEGLContextOnPause(true);
        surfaceView.setEGLContextClientVersion(2);
        surfaceView.setEGLConfigChooser(8, 8, 8, 8, 16, 0); // Alpha used for plane blending.
        surfaceView.setRenderer(this);
        surfaceView.setRenderMode(GLSurfaceView.RENDERMODE_CONTINUOUSLY);
        surfaceView.setWillNotDraw(false);

        installRequested = false;
    }

    @Override
    protected void onResume() {
        super.onResume();

        if (session == null) {
            Exception exception = null;
            String message = null;
            try {
                switch (ArCoreApk.getInstance().requestInstall(this, !installRequested)) {
                    case INSTALL_REQUESTED:
                        installRequested = true;
                        return;
                    case INSTALLED:
                        break;
                }

                // ARCore requires camera permissions to operate. If we did not yet obtain runtime
                // permission on Android M and above, now is a good time to ask the user for it.
                if (!CameraPermissionHelper.hasCameraPermission(this)) {
                    CameraPermissionHelper.requestCameraPermission(this);
                    return;
                }

                // Creates the ARCore session.
                session = new Session(/* context= */ this);
                if (!session.isDepthModeSupported(Config.DepthMode.RAW_DEPTH_ONLY)) {
                    message = "This device does not support the ARCore Raw Depth API. See" +
                                "https://developers.google.com/ar/devices for a list of devices that do.";
                }
            } catch (UnavailableArcoreNotInstalledException
                    | UnavailableUserDeclinedInstallationException e) {
                message = "Please install ARCore";
                exception = e;
            } catch (UnavailableApkTooOldException e) {
                message = "Please update ARCore";
                exception = e;
            } catch (UnavailableSdkTooOldException e) {
                message = "Please update this app";
                exception = e;
            } catch (UnavailableDeviceNotCompatibleException e) {
                message = "This device does not support AR";
                exception = e;
            } catch (Exception e) {
                message = "Failed to create AR session";
                exception = e;
            }

            if (message != null) {
                messageSnackbarHelper.showError(this, message);
                Log.e(TAG, "Exception creating session", exception);
                return;
            }
        }

        try {
            // Enable raw depth estimation and auto focus mode while ARCore is running.
            Config config = session.getConfig();
            config.setDepthMode(Config.DepthMode.RAW_DEPTH_ONLY);
            config.setFocusMode(Config.FocusMode.AUTO);
            session.configure(config);
            session.resume();
        } catch (CameraNotAvailableException e) {
            messageSnackbarHelper.showError(this, "Camera not available. Try restarting the app.");
            session = null;
            return;
        }

        // Note that order matters - see the note in onPause(), the reverse applies here.
        surfaceView.onResume();
        displayRotationHelper.onResume();
        messageSnackbarHelper.showMessage(this, "Waiting for depth data...");
    }

    @Override
    public void onPause() {
        super.onPause();
        if (session != null) {
            // Note that the order matters - GLSurfaceView is paused first so that it does not try
            // to query the session. If Session is paused before GLSurfaceView, GLSurfaceView may
            // still call session.update() and get a SessionPausedException.
            displayRotationHelper.onPause();
            surfaceView.onPause();
            session.pause();
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] results) {
        super.onRequestPermissionsResult(requestCode, permissions, results);
        if (!CameraPermissionHelper.hasCameraPermission(this)) {
            Toast.makeText(this, "Camera permission is needed to run this application",
                    Toast.LENGTH_LONG).show();
            if (!CameraPermissionHelper.shouldShowRequestPermissionRationale(this)) {
                // Permission denied with checking "Do not ask again".
                CameraPermissionHelper.launchPermissionSettings(this);
            }
            finish();
        }
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        FullScreenHelper.setFullScreenOnWindowFocusChanged(this, hasFocus);
    }

    @Override
    public void onSurfaceCreated(GL10 gl, EGLConfig config) {
        GLES20.glClearColor(0.1f, 0.1f, 0.1f, 1.0f);

        // Prepare the rendering objects. This involves reading shaders, so may throw an IOException.
        try {
            // Create the texture and pass it to ARCore session to be filled during update().
            backgroundRenderer.createOnGlThread(/*context=*/ this);
            depthRenderer.createOnGlThread(/*context=*/ this);
            boxRenderer.createOnGlThread(/*context=*/this);
        } catch (IOException e) {
            Log.e(TAG, "Failed to read an asset file", e);
        }
    }

    @Override
    public void onSurfaceChanged(GL10 gl, int width, int height) {
        displayRotationHelper.onSurfaceChanged(width, height);
        GLES20.glViewport(0, 0, width, height);
    }

    @RequiresApi(api = Build.VERSION_CODES.O)
    @Override
    public void onDrawFrame(GL10 gl) {
        // Clear screen to notify driver it should not load any pixels from previous frame.
        GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT | GLES20.GL_DEPTH_BUFFER_BIT);

        if (session == null) {
            return;
        }
        // Notify ARCore session that the view size changed so that the perspective matrix and
        // the video background can be properly adjusted.
        displayRotationHelper.updateSessionIfNeeded(session);

        Image rgb = null, depth = null, confidence = null;
        try {
            session.setCameraTextureName(backgroundRenderer.getTextureId());

            // Obtain the current frame from ARSession. When the configuration is set to
            // UpdateMode.BLOCKING (it is by default), this will throttle the rendering to the
            // camera framerate.
            Frame frame = session.update();
            Camera camera = frame.getCamera();

            // If frame is ready, render camera preview image to the GL surface.
            backgroundRenderer.draw(frame);

            // Retrieve the depth data for this frame.
            FloatBuffer points = DepthData.create(frame, session.createAnchor(camera.getPose()));
            if (points == null) {
                return;
            }

            if (messageSnackbarHelper.isShowing() && points != null) {
                messageSnackbarHelper.hide(this);
            }

            // If not tracking, show tracking failure reason instead.
            if (camera.getTrackingState() == TrackingState.PAUSED) {
                messageSnackbarHelper.showMessage(
                        this, TrackingStateHelper.getTrackingFailureReasonString(camera));
                return;
            }

            // Filter the depth data.
            DepthData.filterUsingPlanes(points, session.getAllTrackables(Plane.class));

            // Visualize depth points.
            depthRenderer.update(points);
            depthRenderer.draw(camera);

            // Draw boxes around clusters of points.
           // PointClusteringHelper clusteringHelper = new PointClusteringHelper(points);
           // List<AABB> clusters = clusteringHelper.findClusters();
//            for (AABB aabb : clusters) {
//                boxRenderer.draw(aabb, camera);
//            }

            if (capture){
                rgb = frame.acquireCameraImage();
                depth = frame.acquireRawDepthImage();
                confidence = frame.acquireRawDepthConfidenceImage();

                sendData(rgb, depth, confidence);

                capture = false;
            }
        } catch (Throwable t) {
            // Avoid crashing the application due to unhandled exceptions.
            Log.e(TAG, "Exception on the OpenGL thread", t);
        } finally {
            if (rgb!=null) rgb.close();
            if (depth!=null) depth.close();
            if (confidence!=null) confidence.close();
        }
    }

    @RequiresApi(api = Build.VERSION_CODES.O)
    private void sendData(Image rgb, Image depth, Image conf){
        File f_rgb=null, f_depth=null;
        try {
            f_rgb = File.createTempFile("rgb", ".jpg");
            f_depth = File.createTempFile("depth", ".png");

            FileOutputStream fos_rgb = new FileOutputStream(f_rgb);
            FileOutputStream fos_depth = new FileOutputStream(f_depth);

            // save rgb to file
            Bitmap bm_rgb = YUV2Bitmap.convert(this, rgb);
            bm_rgb.compress(Bitmap.CompressFormat.JPEG, 100, fos_rgb);
            fos_rgb.flush();
            fos_rgb.close();

            //save depth to file
            ByteBuffer buffer_depth = depth.getPlanes()[0].getBuffer();
            ByteBuffer buffer_conf = conf.getPlanes()[0].getBuffer();
            byte[] bytes_depth = new byte[buffer_depth.capacity()];
            byte[] bytes_conf = new byte[buffer_conf.capacity()];
            buffer_depth.get(bytes_depth);
            buffer_conf.get(bytes_conf);
            byte b1, b2;
            for (int i=0; i<bytes_conf.length; i++){
                if (/* bytes_conf[i]<0.3f || */ bytes_depth[i*2]>8){
                    bytes_depth[i*2] = 0;
                    bytes_depth[i*2+1] = 0;
                }
            }
            fos_depth.write(bytes_depth); // to be formatted in server
            fos_depth.flush();
            fos_depth.close();

            MultipartUtility multipart = new MultipartUtility(IP);
            multipart.addFilePart("rgb", f_rgb);
            multipart.addFilePart("depth", f_depth);
            multipart.finish();
        } catch (IOException e) {
            e.printStackTrace();
        } finally {
            if (f_rgb!=null) f_rgb.delete();
            if (f_depth!=null) f_depth.delete();
        }
    }

    public void onSavePicture(View view){
        capture = !capture;
//        if (capture){
//            captureButton.setText("Stop Capture");
//        } else {
//            captureButton.setText("Start Capture");
//        }
    }

    private void save_rgb(Bitmap bitmap, String fn){
        File out = new File(
                Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_PICTURES) + "/MobileScan",
                fn + ".jpg");
        if (!out.getParentFile().exists()) {
            out.getParentFile().mkdirs();
        }

        FileOutputStream fos = null;
        try {
            out.createNewFile();
            fos = new FileOutputStream(out);
            bitmap.compress(Bitmap.CompressFormat.JPEG, 100, fos);
            fos.flush();
            fos.close();

//            messageSnackbarHelper.showMessage(MainActivity.this, out.getName() + " saved!");
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    private void save_depth(Image image, String fn){
        File out = new File(
                Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_PICTURES) + "/MobileScan",
                fn + ".png");
        if (!out.getParentFile().exists()) {
            out.getParentFile().mkdirs();
        }

        int w = image.getWidth();
        int h = image.getHeight();
        ByteBuffer buffer = image.getPlanes()[0].getBuffer();
        byte[] bytes = new byte[w * h * 2]; // each pixel depth in image is saved in 2bytes
        buffer.get(bytes);

        int pixel, i=0;
        Bitmap bitmap = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888);
        for (int x=0; x<w; x++){
            for (int y=0; y<h; y++){
                pixel = bytes[i++];
                pixel = (pixel << 8) | bytes[i++];
                bitmap.setPixel(x, y, pixel);
            }
        }

        FileOutputStream fos = null;
        try {
            out.createNewFile();
            fos = new FileOutputStream(out);
            bitmap.compress(Bitmap.CompressFormat.JPEG, 100, fos);
            fos.flush();
            fos.close();

//            messageSnackbarHelper.showMessage(MainActivity.this, out.getName() + " saved!");
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}